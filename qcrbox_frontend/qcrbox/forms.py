from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group, Permission

from .models import *


# Workflow Initialisation Forms

class UploadFileForm(forms.Form):

    file = forms.FileField(label='', help_text='')
    group = forms.ChoiceField(choices=[])

    def __init__(self, *args, user, **kwargs):
        super(UploadFileForm, self).__init__(*args, **kwargs)

        # Determine which groups the user is able to tag the file to
        # If they have global access, may pick any group
        if user.has_perm('qcrbox.global_access'):
            qset = Group.objects.all()

        # Otherwise only groups the user belongs to
        else:
            qset = user.groups.all()

        CHOICES = [(g.pk, str(g)) for g in qset.all()]
        self.fields['group'].choices = CHOICES

class LoadFileForm(forms.Form):

    file = forms.ChoiceField(choices=[])

    def __init__(self, *args, user, **kwargs):
        super(LoadFileForm, self).__init__(*args, **kwargs)

        # Determine which groups the user is able to load files from
        # If they have global access, may pick file from any group
        if user.has_perm('qcrbox.global_access'):
            permitted_groups = Group.objects.all()

        # Otherwise restrict visibility and selection to files attached to groups the user belongs to
        else:
            permitted_groups = user.groups.all()

        qset = FileMetaData.objects.filter(group__in=permitted_groups)
        CHOICES = [(f.pk, f.filename) for f in qset.all()]

        self.fields['file'].choices = CHOICES


# Workflow Forms

class SelectApplicationForm(forms.Form):

    application = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        super(SelectApplicationForm, self).__init__(*args, **kwargs)

        qset = Application.objects.all()
        CHOICES = [(a.pk, a.name) for a in qset.filter(active=True)]

        self.fields['application'].choices = CHOICES


# User management forms

class RegisterUserForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class':'form-control'}))
    first_name = forms.CharField(max_length=30,widget=forms.TextInput(attrs={'class':'form-control'}))
    last_name = forms.CharField(max_length=30,widget=forms.TextInput(attrs={'class':'form-control'}))
    user_groups = forms.ModelMultipleChoiceField(queryset=Group.objects.none(), widget=forms.SelectMultiple(attrs={'class': 'form-control'}))

    # Add option to give new users the 'edit users' (group manager) and 'global access' permissions
    group_manager = forms.BooleanField(required=False)
    data_manager = forms.BooleanField(required=False)

    # Disable the global_access checkbox by default
    global_access = forms.BooleanField(required=False, disabled=True, widget=forms.HiddenInput())

    def __init__(self, *args, user, **kwargs):
        super(RegisterUserForm, self).__init__(*args,**kwargs)

        self.fields['username'].widget.attrs['class']='form-control'
        self.fields['password1'].widget.attrs['class']='form-control'
        self.fields['password2'].widget.attrs['class']='form-control'

        # Modify form based on whether creating user has global access
        if user.has_perm('qcrbox.global_access'):
            # Let user pick any group(s) for new user
            self.fields['user_groups'].queryset=Group.objects.all()

            # Unhide and enable the global_access field
            self.fields['global_access'].disabled = False
            self.fields['global_access'].widget = forms.CheckboxInput()

        else:
            # Let user pick groups for new user based on membership of creating user
            self.fields['user_groups'].queryset=user.groups.all()

class UpdateUserForm(forms.ModelForm):

    class Meta:
        model=User
        fields=['first_name','last_name','email','groups']


# Group management forms

class GroupForm(forms.ModelForm):

    class Meta:
        model=Group
        fields=['name']
