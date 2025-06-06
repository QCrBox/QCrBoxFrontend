from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.decorators import permission_required, login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse

import random
import string

from . import forms
from . import models

# ==============================================
# ========== Utiliy functions/classes ==========
# ==============================================

# Define a collection of field properties to pass to tabular display pages
class display_field(object):
    def __init__(self,name,attr,is_header=False,is_special=False):
        # the human-readable name of the attribute
        self.name = name
        # the name of the related model field
        self.attr = attr
        # allow for conditional styling of 'header' field data
        self.is_header = is_header
        # allow for displaying data with some other format
        self.is_special = is_special

# Generic deletion view
def delete_generic(request,Model,type,link_suffix,id,user_is_affiliated):

    # If user is flagged as able to access unaffiliated data, always continue
    if request.user.has_perm('qcrbox.global_access'):
        pass

    # Allow for an access-point check if a user is affiliated with the company to with the data pertains,
    # to prevent users editing things they shouldnt
    elif not user_is_affiliated:
        raise PermissionDenied()

    try:
        instance=Model.objects.get(pk=id)

    except Model.DoesNotExist:
        messages.success(request, f'{type} was deleted succesfully.')    
        return redirect('view_'+link_suffix)

    instance_string=str(instance)
    instance.delete()

    messages.success(request,f'{type} "{instance_string}" was deleted succesfully!')
    return redirect('view_'+link_suffix)


# ============================================
# ========== Workflow-related views ==========
# ============================================

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


# ===================================================
# ========== User management-related views ==========
# ===================================================

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

            # Populate the user info
            new_user.first_name = form.cleaned_data['first_name']
            new_user.last_name = form.cleaned_data['last_name']
            new_user.email = form.cleaned_data['email']
            new_user.save()

            # Add user to the selected user group
            for user_group in user_groups.all():

                user_group.user_set.add(new_user)

            # Add non-group related permissions
            if form.cleaned_data['group_manager']:
                new_user.user_permissions.add(Permission.objects.get(codename='edit_users') )

            if form.cleaned_data['global_access']:
                new_user.user_permissions.add(Permission.objects.get(codename='global_access') )

            messages.success(request,'Registration Successful!')
            form = forms.RegisterUserForm(user=request.user)
    else:
        form = forms.RegisterUserForm(user=request.user)

    return render(request, 'create_generic.html',{
        'form':form,
        'instance_name':'User',
    })

@permission_required('qcrbox.edit_users', raise_exception = True)
def view_users(request):

    fields = [
        display_field('Username','username',is_header=True),
        display_field('First Name','first_name'),
        display_field('Last Name','last_name'),
        display_field('Group(s)','groups',is_special=True),
        ]

    # If a user can view unaffiliated data, they can view it all
    if request.user.has_perm('qcrbox.global_access'):
        object_list=User.objects.all()
    else:
        object_list=User.objects.filter(groups__in=request.user.groups.all())

    object_list=object_list.order_by('username')
    p = Paginator(object_list, 13)
    page=request.GET.get('page')

    try:
        objects = p.get_page(page)
    except PageNotAnInteger:
        objects = p.page(1)
    except EmptyPage:
        objects = p.page(p.num_pages)

    return render(request,'view_list_generic.html',{
        'objects': objects,
        'type':'User',
        'fields':fields,
        'edit_perms':request.user.has_perm('qcrbox.edit_users'),
        'edit_link':'',
        'delete_link':'delete_user',
        'create_link':'create_user',
    })

@permission_required('qcrbox.edit_users', raise_exception=True)
def delete_user(request,user_id):

    deletion_user_groups = User.objects.get(pk=user_id).groups.all()
    current_user_groups = request.user.groups.all()

    shared_groups = deletion_user_groups & current_user_groups
    print(shared_groups)

    return delete_generic(
        request=request,
        Model=User,
        type='User',
        link_suffix='users',
        id=user_id,
        user_is_affiliated = not(shared_groups.exists())
    )

# ====================================================
# ========== Group Management related views ==========
# ====================================================

# Can only edit groups if user has the global access perm
@permission_required('qcrbox.global_access')
def create_group(request):

    if request.method == 'POST':

        # Get the posted form
        form = forms.GroupForm(request.POST)

        if form.is_valid():
            name = form.data['name']
            form.save()
            messages.success(request,(f'New Group "{name}" added!'))
    else:
        form = forms.GroupForm()

    return render(request,'create_generic.html',{
        'form':form,
        'instance_name':'Group',
    })

@login_required(login_url='login')
def view_groups(request):

    fields = [
        display_field('Name','name',is_header=True),
        display_field('Owner(s)','owners',is_special=True),
        display_field('# Members','membership',is_special=True),
        ]

    # If a user can view unaffiliated data, they can view it all
    if request.user.has_perm('qcrbox.global_access'):
        object_list=Group.objects.all()
    else:
        object_list=request.user.groups.all()

    object_list=object_list.order_by('name')
    p = Paginator(object_list, 13)
    page=request.GET.get('page')

    try:
        objects = p.get_page(page)
    except PageNotAnInteger:
        objects = p.page(1)
    except EmptyPage:
        objects = p.page(p.num_pages)

    return render(request,'view_list_generic.html',{
        'objects': objects,
        'type':'Group',
        'fields':fields,
        'edit_perms':request.user.has_perm('qcrbox.global_access'),
        'edit_link':'',
        'delete_link':'delete_group',
        'create_link':'create_group',
    })

@permission_required('qcrbox.global_access', raise_exception=True)
def delete_group(request,group_id):

    # User should have both global access AND edit permissions to be able to do this
    if not request.user.has_perm('qcrbox.edit_users'):
        raise PermissionDenied

    return delete_generic(
        request=request,
        Model=Group,
        type='Group',
        link_suffix='groups',
        id=group_id,
        user_is_affiliated = True,
    )