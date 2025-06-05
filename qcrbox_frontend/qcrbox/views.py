from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse

import random
import string

from . import forms
from . import models


# Workflow-related views

@login_required(login_url='login')
def landing(request):

    # Landing page redirects to workflow initialisation, or login if user not logged in
    return redirect('initialise_workflow')

@login_required(login_url='login')
def initialise_workflow(request):

    # Check if user submitted a form
    if request.method == "POST":

        if 'file' in request.POST:

            # If user chose to load pre-existing file, fetch that file's ID
            redirect_pk = request.POST['file']

        else:

            # If user uploads new file
            file = request.FILES['file']

            # API HOOK upload file to backend, fetch file backend UUID

            # Save file's metadata in local db
            newfile = models.FileMetaData(
                filename= str(file),
                user=request.user,
                group=Group.objects.get(pk=request.POST['group'])
            )
            newfile.save()

            redirect_pk = newfile.pk

        # Redirect to workflow page for the selected file either way
        return redirect('workflow', file_id=redirect_pk)

    # Else return initialise workflow page
    return render(
        request,
        'initial.html',
        {
            'loadfile_form':forms.LoadFileForm(user=request.user),
            'newfile_form':forms.UploadFileForm(user=request.user),
        }
    )

@login_required(login_url='login')
def workflow(request, file_id):

    # Setup context dict to be populated throughout
    context = {}

    # Fetch the current file from the file_id passed in url
    load_file = models.FileMetaData.objects.get(pk=file_id)
    context['file'] = load_file

    # Fetch the app selection form for session selection
    context['select_application_form'] = forms.SelectApplicationForm()

    # Check if user submitted a form
    if request.method == "POST":

        # Check user actually picked an application
        if 'application' in request.POST:
            current_application = models.Application.objects.get(pk=request.POST['application'])
            context['current_application']=current_application

            # Check if user submitted using the 'start session' form
            if 'startup' in request.POST:
                print('startup here')

                context['session_in_progress'] = True

                # API HOOK start interactive session in new tab here

            # Check if user submitted using the 'end session' form
            elif 'end_session' in request.POST:

                # API HOOK get info of newly processed file from backend

                # -==-==-==-==-Placeholder assume new file is created-==-==-==-==-

                run_complete = True

                # -==-==-==-==- Placeholder End -==-==-==-==-

                # If it was possible to get an outfile from the session via the API
                if run_complete:

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
                        group=load_file.group,
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

                else:

                    # If session did not produce output file
                    messages.warning(request, 'No output was produced in the interactive session.')
                    context['session_in_progress'] = True

                    # Then proceed normally

    # Populate the workflow diagram with all steps leading up to the current file
    prior_steps = []
    current_file = load_file

    # While working on a step with a creation history...
    while current_file.processed_by.all():
        prior_step = current_file.processed_by.first()
        prior_steps = [prior_step] + prior_steps

        # Move one step back if possible
        current_file = prior_step.infile

        # Failsafe for if the prior step is malformed
        if not hasattr(current_file,'processed_by'):
            break

    # Add results of the prior step finder to the context
    context['prior_steps'] = prior_steps

    return render(request, 'workflow.html', context)


@login_required(login_url='login')
def download(request, file_id):

    # Fetch permitted groups based on the user's membership
    if request.user.has_perm('qcrbox.global_access'):
        # If user has the global access permission, ALL groups are visible
        allowed_groups = Group.objects.all()
    else:
        # Else, restrict downloads to files linked the groups the user is a member of
        allowed_groups = request.user.groups.all()

    # Fetch the metadata
    download_file_meta = models.FileMetaData.objects.get(pk=file_id)

    # Stop user accessing data from a group they have no access to
    if download_file_meta.group not in allowed_groups:
        raise PermissionDenied

    # API HOOK get file from backend to give to frontend

    # -==-==-==-==-Placeholder generating dummy file to serve-==-==-==-==-

    import csv
    from io import StringIO

    csvfile = StringIO()
    csvwriter = csv.writer(csvfile)

    def read_and_flush():
        csvfile.seek(0)
        data = csvfile.read()
        csvfile.seek(0)
        csvfile.truncate()
        return data

    def data():
        csvwriter.writerow(['name','uuid','type'])
        csvwriter.writerow([download_file_meta.filename, download_file_meta.backend_uuid, download_file_meta.filetype])
        data = read_and_flush()
        yield data

    # -==-==-==-==- Placeholder End -==-==-==-==-

    # Deliver the file using the filename stored in metadata
    response = HttpResponse(data())
    response['Content-Disposition'] = 'attachment; filename='+download_file_meta.filename
    return response


# User management-related views

# Basic login view
def login_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request,user)
            messages.success(request,'Login Successful: Welcome, '+str(request.user))
            return redirect('landing')
        else:
            messages.warning(request,('Login failed, try again!'))

    return render(request, 'login.html', {})

# Basic logout view
@login_required(login_url='login')
def logout_view(request):

    username = request.user.username
    logout(request)
    messages.success(request,('Logout Successful!'))

    return redirect('login')

@permission_required('qcrbox.edit_users', raise_exception = True)
def create_user(request):

    if request.method == 'POST':

        form = forms.RegisterUserForm(request.POST,user=request.user)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']

            # Collect pk of desired user type from form checkboxes
            user_groups = form.cleaned_data['user_groups']

            # Fetch the user we just created
            new_user = User.objects.get(username=username)

            # Add user to the selected user group
            for user_group in user_groups.all():

                user_group.user_set.add(new_user)

            # Add non-group related permissions
            if form.cleaned_data['group_manager']:
                print(Permission.objects.first())
                new_user.user_permissions.add(Permission.objects.get(codename='edit_users') )

            if form.cleaned_data['global_access']:
                new_user.user_permissions.add(Permission.objects.get(codename='global_access') )

            messages.success(request,'Registration Successful!')
            form = forms.RegisterUserForm(user=request.user)
    else:
        form = forms.RegisterUserForm(user=request.user)

    return render(request, 'create_user.html',{'form':form})
