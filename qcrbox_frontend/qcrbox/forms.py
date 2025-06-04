from django import forms
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
