from django.shortcuts import render, redirect
from .plotly_dash import plotly_app
from . import forms
from . import models

# Create your views here.

def landing(request):

    return redirect('initialise_workflow')

def initialise_workflow(request):

    if request.method == "POST":

        if 'file' in request.POST:

            # If user loaded pre-existing file

            redirect_pk = request.POST['file']

        else:

            # If user uploads new file

            file = request.FILES['file']
            newfile = models.FileMetaData(
                filename= str(file),
                user=request.user,
                group=request.user.groups.first()
            )
            newfile.save()

            redirect_pk = newfile.pk

        return redirect('workflow', file_id=redirect_pk)


    return render(
        request,
        'initial.html',
        {
            'loadfile_form':forms.LoadFileForm(user=request.user),
            'newfile_form':forms.UploadFileForm(),
        }
    )

def workflow(request, file_id):

    load_file = models.FileMetaData.objects.get(pk=file_id)

    prior_steps = []
    current_file = load_file

    while current_file.processed_by.all():
        prior_step = current_file.processed_by.first()
        prior_steps = [prior_step] + prior_steps
        current_file = prior_step.infile

        # Failsafe for if the prior step is malformed
        if not hasattr(current_file,'processed_by'):
            break

    return render(
        request,
        'workflow.html',
        {
            'file' : load_file,
            'prior_steps' : prior_steps,
        }
    )