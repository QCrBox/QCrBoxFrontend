from django.shortcuts import render, redirect
from .plotly_dash import plotly_app

import random
import string

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

            # API HOOK upload file to backend, fetch file backend UUID

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

    context = {}

    load_file = models.FileMetaData.objects.get(pk=file_id)

    if request.method == "POST":

        if 'application' in request.POST:
            current_application = models.Application.objects.get(pk=request.POST['application'])
            context['current_application']=current_application

            # Handle starting the external applications:

            if 'startup' in request.POST:
                print('startup here')

                context['session_in_progress'] = True

                # API HOOK start interactive session in new tab here

            elif 'end_session' in request.POST:

                # API HOOK get info of newly processed file from backend

                # -==-==-==-==-Placeholder file creation-==-==-==-==-

                try:
                    old_name = load_file.filename.split('_')
                    new_name = '_'.join(old_name[:-1])+'_'+str(int(old_name[-1])+1)
                except:
                    new_name = load_file.filename + '_1'

                new_uuid = ''.join(random.choices(string.ascii_letters, k=10))

                new_filetype = '.something'

                # -==-==-==-==- Placeholder End -==-==-==-==-

                # Create record for new file's metadata

                newfile = models.FileMetaData(
                    filename= new_name,
                    user=request.user,
                    group=request.user.groups.first(),
                    backend_uuid=new_uuid,
                    filetype= new_filetype
                )
                newfile.save()
                newfile.pk

                # Create record for workflow step

                newprocessstep = models.ProcessStep(
                    application = current_application,
                    infile = load_file,
                    outfile = newfile,
                    )
                newprocessstep.save()

                # Redirect to workflow for new file

                return redirect('workflow', file_id=newfile.pk)


    prior_steps = []
    current_file = load_file

    while current_file.processed_by.all():
        prior_step = current_file.processed_by.first()
        prior_steps = [prior_step] + prior_steps
        current_file = prior_step.infile

        # Failsafe for if the prior step is malformed
        if not hasattr(current_file,'processed_by'):
            break

    context['file'] = load_file
    context['prior_steps'] = prior_steps
    context['select_application_form'] = forms.SelectApplicationForm()

    return render(request, 'workflow.html', context)