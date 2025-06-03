from django import forms
from .models import *

class UploadFileForm(forms.Form):

    file = forms.FileField(label='', help_text='')

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
        CHOICES = [(f.pk, f.name) for f in qset.all()]

        self.fields['application'].choices = CHOICES
