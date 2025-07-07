'''QCrBox Forms

A collection of django-created form classes to be passed to templates as
context arguments to generate interactive HTML forms.

'''

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group

from . import models


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

        super(UploadFileForm, self).__init__(*args, **kwargs)

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

        super(LoadFileForm, self).__init__(*args, **kwargs)

        # Determine which groups the user is able to load files from
        # If they have global access, may pick file from any group
        if user.has_perm('qcrbox.global_access'):
            permitted_groups = Group.objects.all()

        # Otherwise restrict visibility and selection to files attached to groups the user
        # belongs to
        else:
            permitted_groups = user.groups.all()

        qset = models.FileMetaData.objects.filter(active=True).filter(group__in=permitted_groups)
        choices = [(f.pk, f.display_filename) for f in qset.all()]

        self.fields['file'].choices = choices


# Workflow Forms

class SelectApplicationForm(forms.Form):
    '''A Django form to allow selecting an Application as part of initialising
    an Interactive Session.

    Has the following fields:
        - application(ChoiceField): the application to be used.

    '''

    application = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        '''An additional form initialisation step to populate the choices in
        the application field by running a db query to fetch known active
        QCrBox Applications.

        '''

        super(SelectApplicationForm, self).__init__(*args, **kwargs)

        qset = models.Application.objects.all()
        choices = [(a.pk, a.name) for a in qset.filter(active=True)]

        self.fields['application'].choices = choices


# User management forms

class RegisterUserForm(UserCreationForm):
    '''A Django form to facilitate registering a new user.  Based on the
    inbuilt django UserCreationForm.

    Has the following additional fields:
        - email(EmailField): the email address for the new user
        - first_name(CharField): the new user's first name
        - last_name(CharField): the new user's last name
        - user_groups(ModelMultipleChoiceField): allows the selection of one
                or more groups to add the new user to upon creation.
        - group_manager(BooleanField): whether the new user will be given the
                'qcrbox.edit_users' permission.
        - data_manager(BooleanField): whether the new user will be given the
                'qcrbox.edit_data' permission.
        - global_access(BooleanField): whether the new user will be given the
                'qcrbox.global_access' permission.

    '''

    email = forms.EmailField(widget=forms.EmailInput(attrs={'class':'form-control'}))
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class':'form-control'}),
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class':'form-control'}),
    )
    user_groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
    )

    # Add option to give new users the 'edit users' (group manager) and 'global access' permissions
    group_manager = forms.BooleanField(required=False)
    data_manager = forms.BooleanField(required=False)

    # Disable the global_access checkbox by default
    global_access = forms.BooleanField(required=False, disabled=True, widget=forms.HiddenInput())

    def __init__(self, *args, user, **kwargs):

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

        super(RegisterUserForm, self).__init__(*args, **kwargs)

        self.fields['username'].widget.attrs['class'] = 'form-control'
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'

        # Modify form based on whether creating user has global access
        if user.has_perm('qcrbox.global_access'):
            # Let user pick any group(s) for new user
            self.fields['user_groups'].queryset = Group.objects.all()

            # Unhide and enable the global_access field
            self.fields['global_access'].disabled = False
            self.fields['global_access'].widget = forms.CheckboxInput()

        else:
            # Let user pick groups for new user based on membership of creating user
            self.fields['user_groups'].queryset = user.groups.all()

class UpdateUserForm(forms.ModelForm):
    '''A Django ModelForm for admin-level editing of User instances.'''

    class Meta:
        '''Additional ModelForm config'''

        model = User
        fields = ['first_name', 'last_name', 'email', 'groups']

class EditUserForm(forms.ModelForm):
    '''A Django ModelForm for user-level editing User instances.'''

    class Meta:
        '''Additional ModelForm config'''

        model = User
        fields = ['first_name', 'last_name', 'email']


# Group management forms

class GroupForm(forms.ModelForm):
    '''A Django ModelForm for creating or editing Group instances.'''

    class Meta:
        '''Additional ModelForm config'''

        model = Group
        fields = ['name']
