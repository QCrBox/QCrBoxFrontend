'''QCrBox Views

Module containing the view methods which generate and serve http responses to
the browser when their related url is accessed.

'''

import logging
import os

from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.decorators import permission_required, login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.views.static import serve

from . import api, forms, generic, models
from . import workflow as wf
from .plotly_dash import plotly_app
from .utility import DisplayField

LOGGER = logging.getLogger(__name__)

# ============================================
# ========== Workflow-related views ==========
# ============================================

@login_required(login_url='login')
def landing(request):
    '''A basic view to redirect the user to a chosen landing page
    ('initialise_workflow') on accessing the base URL of this web app.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    return redirect('initialise_workflow')

@login_required(login_url='login')
def initialise_workflow(request):
    '''A view to handle the serving and the internal functionality of the
    'initialise_workflow' page; specifically, the ability to upload new files,
    select previously uploaded files and, in each case, initialise a workflow
    based on that file.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    # Check if user submitted a form
    if request.method == 'POST':

        # As the page contains multiple forms, check the contents of POST
        # to identify which was submitted

        if 'file' in request.POST:

            ## Handle file loading here.

            # If user chose to load pre-existing file, fetch that file's ID
            redirect_pk = request.POST['file']

        else:

            ## Handle file uploading here.

            # If no Group selected, fail safely
            if not ('group' in request.POST and request.POST['group']):
                messages.warning(request, 'Must select group to assign to new dataset!')

                return render(
                    request,
                    'initial.html',
                    {
                        'loadfile_form':forms.LoadFileForm(user=request.user),
                        'newfile_form':forms.UploadFileForm(user=request.user),
                    }
                )

            file = request.FILES['file']

            # Check the uploaded file is actually a cif.  If not, fail safely
            if str(file)[-4:] != '.cif':
                messages.warning(request, 'Uploaded files must be .cif!')

                return render(
                    request,
                    'initial.html',
                    {
                        'loadfile_form':forms.LoadFileForm(user=request.user),
                        'newfile_form':forms.UploadFileForm(user=request.user),
                    }
                )

            LOGGER.info(
                'User %s uploading file "%s"',
                request.user.username,
                str(file),
            )

            # Attempt to upload dataset via the API
            api_response = api.upload_dataset(file)

            if not api_response.is_valid:

                LOGGER.error(
                    'File "%s" failed to upload!',
                    str(file),
                )

                messages.warning(request, 'File failed to upload!')
                return redirect('initialise_workflow')

            # Fetch the group to assign to the dataset
            group = Group.objects.get(pk=request.POST['group'])

            # Save the file's FileMetaData
            newfile = wf.save_dataset_metadata(
                request,
                api_response,
                group,
            )

            redirect_pk = newfile.pk

        # Redirect to workflow page for the selected file either way
        return redirect('workflow', file_id=redirect_pk)

    # Else, if mode is GET, return initialise workflow page
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
    '''A view to handle the serving and the internal functionality of the
    'workflow' page.  This includes all Interactive Session functionality;
    the selecting of Applications, launching Interactive Sessions, closing
    Interactive Sessions and fetching any outputs, generating a displaying
    the history of the file the workflow is based on.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - file_id(int): the Frontend db primary key of the dataset being used
            for this workflow.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    # Setup context dict to be populated throughout
    context = {}

    # Fetch the current file from the file_id passed in url
    load_file = models.FileMetaData.objects.get(pk=file_id)
    context['file'] = load_file

    # Get the most recent app list from the API at the start of each workflow, sync the local list
    if not (request.POST and 'application' in request.POST):
        wf.update_apps(request)

    # Fetch the app selection form for session selection
    context['select_application_form'] = forms.SelectApplicationForm()

    # Check if user submitted a form
    if request.method == 'POST':

        # Check user actually picked an application
        if 'application' in request.POST:
            current_application = models.Application.objects.get(pk=request.POST['application'])
            context['current_application'] = current_application

            # Check if user submitted using the 'start session' form
            if 'startup' in request.POST:

                open_session = wf.start_session(
                    request,
                    load_file,
                    current_application,
                )

                if open_session:
                    context['session_in_progress'] = True

            # Check if user submitted using the 'end session' form
            elif 'end_session' in request.POST:

                outfile = wf.close_session(
                    request,
                    load_file,
                    current_application,
                )

                if not outfile:
                    context['session_in_progress'] = True
                elif outfile != 'NO_OUTPUT':
                    return redirect('workflow', file_id=outfile.pk)

    # Populate the workflow diagram with all steps leading up to the current file
    context['prior_steps'] = wf.get_file_history(load_file)

    return render(request, 'workflow.html', context)


# ===================================================
# ========== User management-related views ==========
# ===================================================

def login_view(request):
    '''A view to handle rendering the login page and logging in users.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            LOGGER.info(
                'User %s logged in',
                username,
            )
            messages.success(request, 'Login Successful: Welcome, '+str(request.user))
            return redirect('landing')

        LOGGER.info(
            'User %s failed to log in',
            username,
        )
        messages.warning(request, 'Login failed, try again!')

    return render(request, 'login.html', {})

@login_required(login_url='login')
def logout_view(request):
    '''A view to handle logging out a user.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    username = request.user.username
    logout(request)
    LOGGER.info(
        'User %s logged out',
        username,
    )
    messages.success(request, 'Logout Successful!')

    return redirect('login')

@permission_required('qcrbox.edit_users', raise_exception=True)
def create_user(request):
    '''A view to handle rendering the 'create new user' page and handle the
    creation of a new user on the submittal of the embedded form.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    if request.method == 'POST':

        form = forms.RegisterUserForm(request.POST, user=request.user)
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
                new_user.user_permissions.add(Permission.objects.get(codename='edit_users'))

            if form.cleaned_data['data_manager']:
                new_user.user_permissions.add(Permission.objects.get(codename='edit_data'))

            if form.cleaned_data['global_access']:
                new_user.user_permissions.add(Permission.objects.get(codename='global_access'))

            LOGGER.info(
                'User %s created new user "%s"',
                request.user.username,
                new_user.username,
            )
            messages.success(request, 'Registration Successful!')
            form = forms.RegisterUserForm(user=request.user)
    else:
        form = forms.RegisterUserForm(user=request.user)

    return render(request, 'create_generic.html', {
        'form':form,
        'instance_name':'User',
    })

@login_required(login_url='login')
def view_users(request):
    '''A view to handle generating and rendering the 'view user list' page.
    The contents of this page are filtered based on the request user's
    permissions and are paginated.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    fields = [
        DisplayField('Username', 'username', is_header=True),
        DisplayField('First Name', 'first_name'),
        DisplayField('Last Name', 'last_name'),
        DisplayField('Email', 'email'),
        DisplayField('Group(s)', 'groups', is_special=True),
        DisplayField('Role', 'role', is_special=True),
        ]

    # If a user can view unaffiliated data, they can view it all
    if request.user.has_perm('qcrbox.global_access'):
        object_list = User.objects.all()
    else:
        object_list = User.objects.filter(groups__in=request.user.groups.all())

    object_list = object_list.order_by('username')
    paginator = Paginator(object_list, 13)
    page = request.GET.get('page')

    try:
        objects = paginator.get_page(page)
    except PageNotAnInteger:
        objects = paginator.page(1)
    except EmptyPage:
        objects = paginator.page(paginator.num_pages)

    return render(request, 'view_list_generic.html', {
        'objects': objects,
        'type':'User',
        'fields':fields,
        'edit_perms':request.user.has_perm('qcrbox.edit_users'),
        'edit_link':'edit_user',
        'delete_link':'delete_user',
        'create_link':'create_user',
    })

@permission_required('qcrbox.edit_users', raise_exception=True)
def update_user(request, user_id):
    '''A view to handle rendering the 'edit user' page and handle the
    updating of a user on the submittal of the embedded form.  Based on
    generic.update().

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - user_id(int): the Frontend db primary key of the user being
            edited.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    edit_user_groups = User.objects.get(pk=user_id).groups.all()
    current_user_groups = request.user.groups.all()

    shared_groups = edit_user_groups & current_user_groups

    return generic.update(
        request=request,
        model=User,
        obj_id=user_id,
        meta={
            'obj_type':'User',
            'model_form':forms.UpdateUserForm,
            'link_suffix':'users',
        },
        user_is_affiliated=shared_groups.exists(),
    )

@permission_required('qcrbox.edit_users', raise_exception=True)
def delete_user(request, user_id):
    '''A view to handle the deletion of users.  Based on generic.delete().

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - user_id(int): the Frontend db primary key of the user being
            deleted.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    # Stop an admin accidentally deleting themself
    if int(request.user.pk) == int(user_id):
        messages.warning(request, 'Cannot delete current account from this view.')
        return redirect('view_users')

    deletion_user_groups = User.objects.get(pk=user_id).groups.all()
    current_user_groups = request.user.groups.all()

    shared_groups = deletion_user_groups & current_user_groups

    return generic.delete(
        request=request,
        model=User,
        obj_id=user_id,
        meta={
            'obj_type':'User',
            'link_suffix':'users',
        },
        user_is_affiliated=shared_groups.exists(),
    )


# ====================================================
# ========== Group Management related views ==========
# ====================================================

# Can only edit groups if user has the global access perm
@permission_required('qcrbox.global_access')
def create_group(request):
    '''A view to handle rendering the 'create new group' page and handle the
    creation of a new group on the submittal of the embedded form.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    if request.method == 'POST':

        # Get the posted form
        form = forms.GroupForm(request.POST)

        if form.is_valid():
            name = form.data['name']
            form.save()
            LOGGER.info(
                'User %s created new group "%s"',
                request.user.username,
                name,
            )
            messages.success(request, (f'New Group "{name}" added!'))
    else:
        form = forms.GroupForm()

    return render(request, 'create_generic.html', {
        'form':form,
        'instance_name':'Group',
    })

@login_required(login_url='login')
def view_groups(request):
    '''A view to handle generating and rendering the 'view group list' page.
    The contents of this page are filtered based on the request user's
    permissions and are paginated.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    fields = [
        DisplayField('Name', 'name', is_header=True),
        DisplayField('Owner(s)', 'owners', is_special=True),
        DisplayField('# Members', 'membership', is_special=True),
        ]

    # If a user can view unaffiliated data, they can view it all
    if request.user.has_perm('qcrbox.global_access'):
        object_list = Group.objects.all()
    else:
        object_list = request.user.groups.all()

    object_list = object_list.order_by('name')
    paginator = Paginator(object_list, 13)
    page = request.GET.get('page')

    try:
        objects = paginator.get_page(page)
    except PageNotAnInteger:
        objects = paginator.page(1)
    except EmptyPage:
        objects = paginator.page(paginator.num_pages)

    return render(request, 'view_list_generic.html', {
        'objects':objects,
        'type':'Group',
        'fields':fields,
        'edit_perms':request.user.has_perm('qcrbox.global_access'),
        'edit_link':'edit_group',
        'delete_link':'delete_group',
        'create_link':'create_group',
    })

@permission_required('qcrbox.global_access', raise_exception=True)
def update_group(request, group_id):
    '''A view to handle rendering the 'edit group' page and handle the
    updating of a group on the submittal of the embedded form.  Based on
    generic.update().

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - group_id(int): the Frontend db primary key of the group being
            edited.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    # User should have both global access AND edit permissions to be able to do this
    if not request.user.has_perm('qcrbox.edit_users'):
        raise PermissionDenied

    return generic.update(
        request=request,
        model=Group,
        obj_id=group_id,
        meta={
            'obj_type':'Group',
            'model_form':forms.GroupForm,
            'link_suffix':'groups',
        },
        user_is_affiliated=True
    )

@permission_required('qcrbox.global_access', raise_exception=True)
def delete_group(request, group_id):
    '''A view to handle the deletion of groups.  Based on generic.delete().

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - group_id(int): the Frontend db primary key of the group being
            deleted.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    # User should have both global access AND edit permissions to be able to do this
    if not request.user.has_perm('qcrbox.edit_users'):
        raise PermissionDenied

    return generic.delete(
        request=request,
        model=Group,
        obj_id=group_id,
        meta={
            'obj_type':'Group',
            'link_suffix':'groups',
        },
        user_is_affiliated=True,
    )


# ====================================================
# ========== Data Management related views ===========
# ====================================================

@login_required(login_url='login')
def history_dashboard(request, dataset_id):
    '''A view to handle rendering the page containing the Tree Dashboard
    showing dataset ancestry.

    '''

    return render(request, 'history_dashboard.html', {
        'wide_layout' : True,
        'dash_context' : {'init_pk':{'title':dataset_id}}
    })


# No view for dataset creation (handled through the workflow initialisation page)

@login_required(login_url='login')
def view_datasets(request):
    '''A view to handle generating and rendering the 'view datasets list'
    page.  The contents of this page are filtered based on the request user's
    permissions and are paginated.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    fields = [
        DisplayField('Filename', 'display_filename', is_header=True),
        DisplayField('Group', 'group'),
        DisplayField('Created By', 'user'),
        DisplayField('At Time', 'creation_time'),
        DisplayField('From File', 'created_from', is_special=True),
        DisplayField('With App', 'created_app', is_special=True),
        ]

    object_list = models.FileMetaData.objects.filter(active=True)

    # If a user can view unaffiliated data, they can view it all
    if request.user.has_perm('qcrbox.global_access'):
        pass
    else:
        object_list = object_list.filter(group__in=request.user.groups.objects.all())

    object_list = object_list.order_by('group__name', 'filename')
    paginator = Paginator(object_list, 13)
    page = request.GET.get('page')

    try:
        objects = paginator.get_page(page)
    except PageNotAnInteger:
        objects = paginator.page(1)
    except EmptyPage:
        objects = paginator.page(paginator.num_pages)

    return render(request, 'view_list_generic.html', {
        'objects': objects,
        'type':'Dataset',
        'fields':fields,
        'edit_perms':request.user.has_perm('qcrbox.edit_data'),
        'delete_link':'delete_dataset',
        'history_link':'dataset_history',
    })

@permission_required('qcrbox.edit_data', raise_exception=True)
def delete_dataset(request, dataset_id):
    '''A view to handle sending a 'delete dataset' command to the API and, if
    succesful, flag the Frontend db entry for that dataset as inactive.  This
    does not actually delete any information from the Frontend DB, such that
    the modification history of datasets can be preserved, but disables some
    functionality (e.g. the ability to download or start a workflow) for
    datasets marked as inactive in this way.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - dataset_id(int): the Frontend db primary key of the dataset being
            deleted.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    deletion_data_meta = models.FileMetaData.objects.get(pk=dataset_id)
    deletion_data_group = deletion_data_meta.group
    current_user_groups = request.user.groups.all()

    shared_groups = deletion_data_group in current_user_groups

    # Check credentials before invoking the generic delete, as API will also need calling
    if shared_groups or request.user.has_perm('qcrbox.global_access'):

        LOGGER.info(
            'User %s deleting dataset %s',
            request.user.username,
            deletion_data_meta.display_filename,
        )
        api_response = api.delete_dataset(deletion_data_meta.backend_uuid)

    else:
        raise PermissionDenied

    if not api_response.is_valid:
        LOGGER.error('Could not delete dataset!')
        messages.warning(request, 'API delete request unsuccessful: file not deleted!')
        return redirect('view_datasets')

    try:
        instance = models.FileMetaData.objects.get(pk=dataset_id)

    except models.FileMetaData.DoesNotExist:
        LOGGER.info(
            'User %s attempted to deactivate non-existent File Metadata (pk=%d)',
            request.user.username,
            dataset_id,
        )
        messages.success(request, 'Dataset was deleted succesfully.')
        return redirect('view_datasets')

    # Don't actually delete the local metadata, just flag it as inactive so history can be preserved
    instance.active = False
    instance.save()

    LOGGER.info(
        'User %s flagged File Metadata "%s" as inactive.',
        request.user.username,
        instance.display_filename,
    )
    messages.success(request, f'Dataset "{instance}" was deleted succesfully!')
    return redirect('view_datasets')


@login_required(login_url='login')
def download(request, file_id):
    '''A view to handle fetching the contents of datasets from the Backend
    and serving them to the user as a download.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - file_id(int): the Frontend db primary key of the dataset being
            downloaded.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url, containing the download
            file.

    '''

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
        LOGGER.info(
            'User %s denied permission to download dataset "%s" (unaffiliated)',
            request.user.username,
            download_file_meta.display_filename,
        )
        raise PermissionDenied

    LOGGER.info(
        'User %s downloading dataset "%s"',
        request.user.username,
        download_file_meta.display_filename,
    )
    api_response = api.download_dataset(download_file_meta.backend_uuid)

    if not api_response.is_valid:
        messages.warning(request, 'Could not fetch the requested file!')
        LOGGER.error('Could not find requested dataset!')
        return redirect('initialise_workflow')

    data = api_response.body

    # Deliver the file using the filename stored in metadata
    httpresponse = HttpResponse(data)
    d_filename = download_file_meta.display_filename
    httpresponse['Content-Disposition'] = 'attachment; filename=' + d_filename
    return httpresponse


@login_required(login_url='login')
def visualise(request, dataset_id):

    # Fetch permitted groups based on the user's membership
    if request.user.has_perm('qcrbox.global_access'):
        # If user has the global access permission, ALL groups are visible
        allowed_groups = Group.objects.all()
    else:
        # Else, restrict downloads to files linked the groups the user is a member of
        allowed_groups = request.user.groups.all()

    # Fetch the metadata
    visualise_file_meta = models.FileMetaData.objects.get(pk=dataset_id)

    # Stop user accessing data from a group they have no access to
    if visualise_file_meta.group not in allowed_groups:
        LOGGER.info(
            'User %s denied permission to visualise dataset "%s" (unaffiliated)',
            request.user.username,
            download_file_meta.display_filename,
        )
        raise PermissionDenied

    # Get host name without port, manually prepend http:// to stop django
    # treating this as a relative URL

    hostname = 'http://' + request.get_host().split(':')[0]
    v_url = f'{hostname}:{settings.API_VISUALISER_PORT}/retrieve/{visualise_file_meta.backend_uuid}'
    LOGGER.info(f'Opening Visualiser at "{v_url}"')
    
    return redirect(v_url)

# ====================================================
# =================== Debug Tools ====================
# ====================================================

@login_required(login_url='login')
def frontend_logs(request):
    '''A view to fetch the frontend logs and return them as a download.
    Strictly for debugging purposes only, and only permitted to superusers.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    if not request.user.is_superuser:
        raise PermissionDenied
    filepath = 'qcrbox.log'
    return serve(request, os.path.basename(filepath), os.path.dirname(filepath))
