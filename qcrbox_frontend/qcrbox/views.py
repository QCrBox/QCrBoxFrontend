import random
import string

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.decorators import permission_required, login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse

from . import api
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

# Generic update/edit view
def update_generic(request,Model,ModelForm,type,link_suffix,id,user_is_affiliated=False,**kwargs):

    # If user is flagged as able to access unaffiliated data, always continue
    if request.user.has_perm('qcrbox.global_access'):
        pass

    # Allow for an access-point check if a user is affiliated with the company to with the data pertains,
    # to prevent users editing things they shouldnt    
    elif not user_is_affiliated:
        raise PermissionDenied()

    instance=Model.objects.get(pk=id)
    form=ModelForm(request.POST or None, instance=instance, **kwargs)

    if form.is_valid():
        form.save()

        messages.success(request,('Changes to '+str(instance)+' saved!'))
        return redirect('view_'+link_suffix)

    return render(request,'update_generic.html',{
        'type':type,
        'object':instance,
        'form':form,
        'view_link':'view_'+link_suffix,
        })

# Generic deletion view
def delete_generic(request,Model,type,link_suffix,id,user_is_affiliated=False):

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

            api_response = api.upload_dataset(file)

            if not api_response.is_valid:
                messages.warning(request, 'File failed to upload! '+str(api_response.body))
                return redirect('initialise_workflow')

            else:
                backend_file_id = api_response.body.payload.datasets[0].qcrbox_dataset_id

            # Save file's metadata in local db
            newfile = models.FileMetaData(
                filename= str(file),
                user=request.user,
                group=Group.objects.get(pk=request.POST['group']),
                backend_uuid=backend_file_id
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

                context['session_in_progress'] = True

                api_response = api.start_session(app_id = current_application.pk, dataset_id = load_file.backend_uuid)

                if api_response.is_valid:
                    context['session_in_progress'] = True
                    request.session['app_session_id'] = api_response.body.payload.interactive_session_id

                else:
                    messages.warning(request,'Could not start session! ' + str(api_response.body))

            # Check if user submitted using the 'end session' form
            elif 'end_session' in request.POST:
                
                # If cookie is lost, abort
                if 'app_session_id' not in request.session:
                    messages.warning(request,'Session timed out! Please try again.')
                    return redirect('initialise_workflow')

                app_session_id = request.session['app_session_id']
                api_response = api.get_session(app_session_id)

                # If session can't be found, abort
                if not api_response.is_valid:
                    messages.warning(request,'Session not found! Please try again. ' + str(api_response.body))
                    return redirect('initialise_workflow')
                
                # -==-==-==-==-Placeholder assume new file is created-==-==-==-==-

                outfile_exists = False

                # -==-==-==-==- Placeholder End -==-==-==-==-

                api.close_session(app_session_id)

                # If it was possible to get an outfile from the session via the API
                if outfile_exists:

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

                    # If session did not produce output file, issue a warning
                    messages.warning(request, 'No output was produced in the interactive session.')

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

    api_response = api.download_dataset(download_file_meta.backend_uuid)

    if not api_response.is_valid:
        messages.warning(request,'Could not fetch the requested file! '+str(api_response.body))
        return redirect('initialise_workflow')
    else:
        data = api_response.body

    # Deliver the file using the filename stored in metadata
    httpresponse = HttpResponse(data)
    httpresponse['Content-Disposition'] = 'attachment; filename='+download_file_meta.filename
    return httpresponse


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

            if form.cleaned_data['data_manager']:
                new_user.user_permissions.add(Permission.objects.get(codename='edit_data') )

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

@login_required(login_url='login')
def view_users(request):

    fields = [
        display_field('Username','username',is_header=True),
        display_field('First Name','first_name'),
        display_field('Last Name','last_name'),
        display_field('Email','email'),
        display_field('Group(s)','groups',is_special=True),
        display_field('Role','role',is_special=True),
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
        'edit_link':'edit_user',
        'delete_link':'delete_user',
        'create_link':'create_user',
    })

@permission_required('qcrbox.edit_users', raise_exception=True)
def update_user(request,user_id):

    edit_user_groups = User.objects.get(pk=user_id).groups.all()
    current_user_groups = request.user.groups.all()

    shared_groups = edit_user_groups & current_user_groups

    return update_generic(
        request=request,
        Model=User,
        ModelForm=forms.UpdateUserForm,
        type='User',
        link_suffix='users',
        id=user_id,
        user_is_affiliated = shared_groups.exists()
    )

@permission_required('qcrbox.edit_users', raise_exception=True)
def delete_user(request,user_id):

    # Stop an admin accidentally deleting themself
    if int(request.user.pk) == int(user_id):
        messages.warning(request,'Cannot delete current account from this view; to delete your own account, navigate to profile settings.')
        return redirect('view_users')

    deletion_user_groups = User.objects.get(pk=user_id).groups.all()
    current_user_groups = request.user.groups.all()

    shared_groups = deletion_user_groups & current_user_groups

    return delete_generic(
        request=request,
        Model=User,
        type='User',
        link_suffix='users',
        id=user_id,
        user_is_affiliated = shared_groups.exists()
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
        'edit_link':'edit_group',
        'delete_link':'delete_group',
        'create_link':'create_group',
    })

@permission_required('qcrbox.global_access', raise_exception=True)
def update_group(request,group_id):

    # User should have both global access AND edit permissions to be able to do this
    if not request.user.has_perm('qcrbox.edit_users'):
        raise PermissionDenied

    return update_generic(
        request=request,
        Model=Group,
        ModelForm=forms.GroupForm,
        type='Group',
        link_suffix='groups',
        id=group_id,
        user_is_affiliated = True
    )

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


# ====================================================
# ========== Data Management related views ==========
# ====================================================

# No view for dataset creation (handled through the workflow initialisation page)

@login_required(login_url='login')
def view_datasets(request):

    fields = [
        display_field('Filename','filename',is_header=True),
        display_field('Group','group'),
        display_field('Created By','user'),
        display_field('At Time','creation_time'),
        display_field('From File','created_from',is_special=True),
        display_field('With App','created_app', is_special=True),
        ]

    object_list=models.FileMetaData.objects.all()

    # If a user can view unaffiliated data, they can view it all
    if request.user.has_perm('qcrbox.global_access'):
        pass
    else:
        object_list=object_list.filter(group__in=request.user.groups.objects.all())

    object_list=object_list.order_by('group__name','filename')
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
        'type':'Dataset',
        'fields':fields,
        'edit_perms':request.user.has_perm('qcrbox.edit_data'),
        'delete_link':'delete_dataset',
    })

@permission_required('qcrbox.edit_data', raise_exception=True)
def delete_dataset(request,dataset_id):

    deletion_data_meta = models.FileMetaData.objects.get(pk=dataset_id)
    deletion_data_group = deletion_data_meta.group
    current_user_groups = request.user.groups.all()

    shared_groups = (deletion_data_group in current_user_groups)

    # Check credentials before invoking the generic delete, as API will also need calling
    if shared_groups or request.user.has_perm('qcrbox.global_access'):

        api_response = api.delete_dataset(deletion_data_meta.backend_uuid)

    else:
        raise PermissionDenied

    if api_response.is_valid:
        return delete_generic(
            request=request,
            Model=models.FileMetaData,
            type='Dataset',
            link_suffix='datasets',
            id=dataset_id,
            user_is_affiliated = True
        )

    else:
        messages.warning(request,'API delete request unsuccessful: file not deleted!'+str(api_response.body))
        return redirect('view_datasets')