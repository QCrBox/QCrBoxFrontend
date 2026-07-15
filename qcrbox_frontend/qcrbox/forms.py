'''QCrBox Forms

A collection of django-created form classes to be passed to templates as
context arguments to generate interactive HTML forms.

'''

import json

from django import forms
from django.contrib.auth.models import User, Group
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator

from qcrbox import models
from qcrbox import utility as ut


# Workflow Initialisation Forms

class UploadFileForm(forms.Form):
    '''A Django form to facilitate uploading a new file.

    Has the following fields:
        - file(FileField): allows a user to select a file from their machine
                to upload
        - group(ChoiceField): allows the user to select the group to affiliate
                to this upload, from among groups they are a member of.

    '''

    file = forms.FileField(label='', help_text='')
    group = forms.ChoiceField(choices=[])

    def __init__(self, *args, user, **kwargs):
        '''An additional form initialisation step to populate the choices in
        the group field by running a db query to fetch groups which the current
        user belongs to.

        Additional Parameters:
        - user(User): a django.contrib.auth.models User instance, corresponding
                to the currently logged in user, to determine which groups
                should be given as selection options

        '''

        super().__init__(*args, **kwargs)

        # Determine which groups the user is able to tag the file to
        # If they have global access, may pick any group
        if user.has_perm('qcrbox.global_access'):
            qset = Group.objects.all()

        # Otherwise only groups the user belongs to
        else:
            qset = user.groups.all()

        choices = [(g.pk, str(g)) for g in qset.all()]
        self.fields['group'].choices = choices

class LoadFileForm(forms.Form):
    '''A Django form to facilitate selecting a previously uploaded dataset
    to use to start a new workflow.

    Has the following fields:
        - file(ChoiceField): allows a user to select a dataset those with
                stored in the Frontend db.

    '''

    file = forms.ChoiceField(choices=[])

    def __init__(self, *args, user, **kwargs):
        '''An additional form initialisation step to populate the choices in
        the file field by running a db query to fetch files affiliated with
        a group that the user belongs to.

        Additional Parameters:
        - user(User): a django.contrib.auth.models User instance, corresponding
                to the currently logged in user, to determine which groups
                should be given as selection options

        '''

        super().__init__(*args, **kwargs)

        # Determine which groups the user is able to load files from
        # If they have global access, may pick file from any group
        if user.has_perm('qcrbox.global_access'):
            permitted_groups = Group.objects.all()

        # Otherwise restrict visibility and selection to files attached to groups the user
        # belongs to
        else:
            permitted_groups = user.groups.all()

        objs = models.FileMetaData.objects                              # pylint: disable=no-member
        qset = objs.filter(active=True).filter(group__in=permitted_groups)

        # Filter to only retain the oldest file in each workflow tree, i.e. files which are
        # not the output of any process
        process_objs = models.ProcessStep.objects                       # pylint: disable=no-member
        process_outfiles = process_objs.all().values_list('outfile', flat=True)
        qset = qset.exclude(pk__in=process_outfiles)

        choices = [(f.pk, str(f)) for f in qset.all()]

        self.fields['file'].choices = choices


# Workflow Forms

class DisableableSelect(forms.Select):
    '''A Select widget which renders some options as disabled (greyed out),
    with a tooltip explaining why.'''

    def __init__(self, *args, disabled_choices=None, **kwargs):
        '''Additional Parameters:
        - disabled_choices(dict): maps option values (as strings) to the
                tooltip text shown for the disabled option.

        '''

        self.disabled_choices = disabled_choices or {}
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        tooltip = self.disabled_choices.get(str(value))
        if tooltip is not None:
            option['attrs']['disabled'] = True
            option['attrs']['title'] = tooltip
        return option


class SelectCommandForm(forms.Form):
    '''A Django form to allow selecting an Application as part of initialising
    an Interactive Session.

    Has the following fields:
        - application(ChoiceField): the application to be used.

    '''

    command = forms.ChoiceField(choices=[])

    def __init__(self, *args, disabled_commands=None, **kwargs):
        '''An additional form initialisation step to populate the choices in
        the application field by running a db query to fetch known active
        QCrBox Applications.

        Additional Parameters:
        - disabled_commands(dict): maps AppCommand pks to a tooltip; the
                corresponding options are rendered disabled (commands which
                cannot run on the loaded file).

        '''

        super().__init__(*args, **kwargs)

        qset = models.AppCommand.objects.order_by('app__name','name')   # pylint: disable=no-member
        choices = [(c.pk, ut.sanitize_command_name(c)) for c in qset.filter(app__active=True)]

        self.fields['command'].choices = choices
        if disabled_commands:
            self.fields['command'].widget = DisableableSelect(
                choices=choices,
                disabled_choices={str(pk): tooltip for pk, tooltip in disabled_commands.items()},
            )


# User management forms
#
# Users and groups are managed in lldap (mirrored into Django on login by
# core.auth_backends); only the self-service account form for the non-SSO
# development fallback remains.

class EditUserForm(forms.ModelForm):
    '''A Django ModelForm for user-level editing User instances.'''

    class Meta:                                            # pylint: disable=too-few-public-methods
        '''Additional ModelForm config'''

        model = User
        fields = ['first_name', 'last_name', 'email']


# Automatic form generation to get command parameters from user

class CommandForm(forms.Form):
    '''A Django form which auto-populates itself with fields for each of a
    given command's associated parameters.'''

    def __init__(self, *args, command, dataset, **kwargs):

        '''An additional form initialisation step.  Modifies which fields are
        editable based on the permissions of the creating user, and populates
        the user_groups field's choices with groups to which the creating user
        has access.

        Additional Parameters:
        - user(User): a django.contrib.auth.models User instance, corresponding
                to the currently logged in user, to determine which groups
                should be given as selection options and which form fields if
                any should be disabled.

        '''

        super().__init__(*args, **kwargs)

        # A boolean to track whether the main infile fields has been handled;
        # the first one infile field just take the current file as a default
        # and not be rendered as a widget.

        handled_infile_field = False

        for param in command.parameters.all():

            # The following dtypes are defined for command params:
            # - str
            # - float
            # - int
            # - bool
            # - QCrBox.cif_data_file
            # - QCrBox.output_path
            # - QCrBox.output_cif
            # - QCrBox.data_file

            # Construct kwargs common to all field types
            misc_kwargs = {
                'initial' : None if param.default=='None' else param.default,
                'help_text' : f'<span class=\"tooltiphover\">&nbsp<i class="fa-solid fa-circle-in'\
                              f'fo"></i></span><span class=\"tooltiptext\"><small>'\
                              f'{param.description}</small></span>',
                'required' : param.required,
                'validators' : [],
            }

            # Add appropriate validator(s) for any implemented validation type (except choices)
            if param.validation_type == 'numeric_range':
                nrange = json.loads(param.validation_value)
                misc_kwargs['validators'].append(MinValueValidator(limit_value=min(nrange)))
                misc_kwargs['validators'].append(MaxValueValidator(limit_value=max(nrange)))

            if param.validation_type == 'regex':
                misc_kwargs['validators'].append(RegexValidator(regex=param.validation_value))

            # First check if the validation is 'choice', which overrides the other types of inputs
            # with a ChoiceField

            if param.validation_type == 'choices':
                self.fields[param.name] = forms.ChoiceField(
                    choices=[[c,c] for c in json.loads(param.validation_value)],
                    **misc_kwargs,
                )

            # Then handle the other field types based on dtypes
            elif param.dtype == 'str':
                self.fields[param.name] = forms.CharField(
                    max_length=255,
                    **misc_kwargs,
                )
            elif param.dtype == 'float':
                self.fields[param.name] = forms.FloatField(
                    **misc_kwargs,
                )
            elif param.dtype == 'int':
                self.fields[param.name] = forms.IntegerField(
                    **misc_kwargs,
                )
            elif param.dtype == 'bool':

                # Override requiredness for Boolean fields
                misc_kwargs['required'] = False

                self.fields[param.name] = forms.BooleanField(
                    **misc_kwargs,
                )
            elif param.dtype == 'QCrBox.cif_data_file':

                # Hide the first file input field and populate it with the file of the active
                # workflow
                if not handled_infile_field:
                    handled_infile_field = True
                    self.fields[param.name] = forms.CharField(
                        widget=forms.HiddenInput(),
                        initial=dataset.backend_uuid,
                    )

                # Render any subsequent file input fields as a choice of the dataset's ancestors
                else:

                    ancestors = []

                    dataset_i = dataset
                    steps = models.ProcessStep.objects                  # pylint: disable=no-member

                    # Populate the ancestry
                    while True:
                        prior_step = steps.filter(outfile=dataset_i)
                        if not prior_step.exists():
                            break

                        dataset_i = prior_step.first().infile
                        if dataset_i.active:
                            ancestors.append(dataset_i)

                    self.fields[param.name] = forms.ChoiceField(
                        choices=[(a.backend_uuid, a.display_filename) for a in ancestors[::-1]]
                    )

            # Note: command outputs (QCrBox.output_cif and the QCrBox.output_*
            # artifact types) are declared in the command spec's outputs
            # section, not as parameters, and their filenames are fixed by the
            # spec - so no form fields are needed for them.

            elif param.dtype == 'QCrBox.data_file':

                # Create file upload field which will be handled uniquely in views on submit

                # Set required=False as validation for upload files is handled elsewhere
                self.fields[param.name] = forms.FileField(
                    label=param.name.replace('_',' ').title(),
                    required=False
                )

            else:
                raise NotImplementedError(
                    f'Command contained parameter with illegal dtype "{param.dtype}"!',
                )
