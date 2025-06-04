from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group, Permission

from .models import *

class UploadFileForm(forms.Form):

    file = forms.FileField(label='', help_text='')
    group = forms.ChoiceField(choices=[])

    def __init__(self, *args, user, **kwargs):
        super(UploadFileForm, self).__init__(*args, **kwargs)

        qset = user.groups.all()
        CHOICES = [(g.pk, str(g)) for g in qset.all()]

        self.fields['group'].choices = CHOICES

class LoadFileForm(forms.Form):

    file = forms.ChoiceField(choices=[])

    def __init__(self, *args, user, **kwargs):
        super(LoadFileForm, self).__init__(*args, **kwargs)

        qset = FileMetaData.objects.filter(group__in=user.groups.all())
        CHOICES = [(f.pk, f.filename) for f in qset.all()]

        self.fields['file'].choices = CHOICES

class SelectApplicationForm(forms.Form):

    application = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        super(SelectApplicationForm, self).__init__(*args, **kwargs)

        qset = Application.objects.all()
        CHOICES = [(a.pk, a.name) for a in qset.all()]

        self.fields['application'].choices = CHOICES

# User management forms

class RegisterUserForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class':'form-control'}))
    first_name = forms.CharField(max_length=30,widget=forms.TextInput(attrs={'class':'form-control'}))
    last_name = forms.CharField(max_length=30,widget=forms.TextInput(attrs={'class':'form-control'}))
    user_groups = forms.ModelMultipleChoiceField(queryset=Group.objects.none(), widget=forms.SelectMultiple(attrs={'class': 'form-control'}))
    group_manager = forms.BooleanField(required=False)
    global_access = forms.BooleanField(required=False)

    def __init__(self, *args, user, **kwargs):
        super(RegisterUserForm, self).__init__(*args,**kwargs)

        self.fields['username'].widget.attrs['class']='form-control'
        self.fields['password1'].widget.attrs['class']='form-control'
        self.fields['password2'].widget.attrs['class']='form-control'

        if user.has_perm('qcrbox.global_access'):
            self.fields['user_groups'].queryset=Group.objects.all()
        else:
            self.fields['user_groups'].queryset=user.groups.all()