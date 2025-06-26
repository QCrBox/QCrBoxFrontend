"""QCrBox Views

Module containing the view methods which generate and serve http responses to
the browser when their related url is accessed.

"""

import logging
import os
import re

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.decorators import permission_required, login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.views.static import serve

from . import api
from . import forms
from . import models
from . import utility

logger = logging.getLogger(__name__)

# ==============================================
# ========== Utiliy functions/classes ==========
# ==============================================

class DisplayField():
    '''A class to contain information on fields to be displayed in 'view list'
    e.g. denoting a field which should form a column of a rendered html table
    and some metadata on how it should be rendered.

    '''

    def __init__(self, name, attr, is_header=False, is_special=False):
        '''Initialise an instance of DisplayField

        Parameters:
        - name(str): The human readable name of the field
        - attr(str): The name of the related Model attribute.  This can also
                be a recursive attribute, separated by '__': e.g., setting
                attr to 'dataset__filename' will return the 'filename'
                attribute of the DataSet object referred to in this Models's
                'dataset' attribute.
        - is_header(bool): Whether the column containing this field should be
                styled as a header column
        - is_special(bool): Whether there are any special instructions for
                generating entries in this field.  These are parsed by the
                get_special method in templatetags/getspecial.py

        Returns:
        None

        '''

        self.name = name
        self.attr = attr
        self.is_header = is_header
        self.is_special = is_special


def update_generic(request, Model, ModelForm, obj_type, link_suffix, obj_id, user_is_affiliated=False, **kwargs):
    '''A genericised framework to generate a django response which generates
    and serves a page containing an update form for a given database model,
    and processes the submitting of that form.  This view should never be
    called directly by a user, and as such does not have an associated url;
    this method is instead called by other view methods.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - Model(ModelBase): the base class for the Model which is editable on the
            page returned by this view.
    - ModelForm(Form): the django form for creating/editing instances of the
            chosen Model.
    - obj_type(str): the human-readable name given to instances of the Model, e.g.
            'Application', for display on the page returned by this view.
    - link_suffix(str): the suffix of the URL associated with the 'view list'
            view of the chosen model.  The django IDs of 'View list' view urls
            are standardised in the form 'view_[slug]', where the slug should
            be provided as this parameter.  This is used to generate the
            redirect response upon a succesful form submittal.
    - obj_id(int): the primary key of the instance of the chosen Model which is
            the target of this edit attempt.
    - user_is_affiliated(bool): an optional boolean to denote whether the
            user associated with the request is in some way affiliated with
            the instance being edited (i.e., the user belongs to the Group
            associated with a given Dataset).  If set to False, the user will
            only be given permission to edit the instance if they also have
            the 'qcrbox.global_access' permission.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    # If user is flagged as able to access unaffiliated data, always continue
    if request.user.has_perm('qcrbox.global_access'):
        pass

    # Allow for an access-point check if a user is affiliated with the company to with the data pertains,
    # to prevent users editing things they shouldnt
    elif not user_is_affiliated:
        logger.info(f'User {request.user.username} denied permission to modify {obj_type} (pk={obj_id}) (unaffiliated)')
        raise PermissionDenied()

    instance = Model.objects.get(pk=obj_id)
    form = ModelForm(request.POST or None, instance=instance, **kwargs)

    if form.is_valid():
        form.save()

        logger.info(f'User {request.user.username} updated {obj_type} "{instance}"')
        messages.success(request, f'Changes to "{instance}" saved!')
        return redirect('view_'+link_suffix)

    return render(request, 'update_generic.html', {
        'type':obj_type,
        'object':instance,
        'form':form,
        'view_link':'view_'+link_suffix,
        })


def delete_generic(request, Model, obj_type, link_suffix, obj_id, user_is_affiliated=False):
    '''A genericised framework to generate a django response which processes
    the deletion of a given Model instance.  This view should never be called
    directly by a user, and as such does not have an associated url; this
    method is instead called by other view methods.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - Model(ModelBase): the base class for the Model which is to be deleted.
    - obj_type(str): the human-readable name given to instances of the Model, e.g.
            'Application', for display on the message generated by this view.
    - link_suffix(str): the suffix of the URL associated with the 'view list'
            view of the chosen model.  The django IDs of 'View list' view urls
            are standardised in the form 'view_[slug]', where the slug should
            be provided as this parameter.  This is used to generate the
            redirect response upon a succesful delete request.
    - obj_id(int): the primary key of the instance of the chosen Model which is
            the target of this delete attempt.
    - user_is_affiliated(bool): an optional boolean to denote whether the
            user associated with the request is in some way affiliated with
            the instance being deleted (i.e., the user belongs to the Group
            associated with a given Dataset).  If set to False, the user will
            only be given permission to delete the instance if they also have
            the 'qcrbox.global_access' permission.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    # If user is flagged as able to access unaffiliated data, always continue
    if request.user.has_perm('qcrbox.global_access'):
        pass

    # Allow for an access-point check if a user is affiliated with the company to with the data pertains,
    # to prevent users editing things they shouldnt
    elif not user_is_affiliated:
        logger.info(f'User {request.user.username} denied permission to delete {obj_type} (pk={obj_id}) (unaffiliated)')
        raise PermissionDenied()

    try:
        instance = Model.objects.get(pk=obj_id)

    except Model.DoesNotExist:
        logger.info(f'User {request.user.username} attempted to delete non-existent {obj_type} (pk={obj_id})')
        messages.success(request, f'{obj_type} was deleted succesfully.')
        return redirect('view_'+link_suffix)

    instance_string = str(instance)
    instance.delete()

    logger.info(f'User {request.user.username} deleted {obj_type} "{instance_string}"')
    messages.success(request, f'{obj_type} "{instance_string}" was deleted succesfully!')
    return redirect('view_'+link_suffix)


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
    if request.method == "POST":

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

            logger.info(f'User {request.user.username} uploading file "{str(file)}"')

            # Attempt to upload dataset via the API
            api_response = api.upload_dataset(file)

            if not api_response.is_valid:
                logger.error(f'File "{str(file)}" failed to upload!')
                messages.warning(request, 'File failed to upload!')
                return redirect('initialise_workflow')

            backend_file_id = api_response.body.payload.datasets[0].qcrbox_dataset_id

            # Save file's metadata in local db
            newfile = models.FileMetaData(
                filename=str(file),
                display_filename=str(file),
                user=request.user,
                group=Group.objects.get(pk=request.POST['group']),
                backend_uuid=backend_file_id
            )
            newfile.save()
            logger.info(f'Metadata for file {str(file)} saved, backend_uuid={backend_file_id}')

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
        update_response = utility.update_applications()
        if not update_response:
            messages.warning(request, 'Warning: could not update applications list!')
            logger.log('Could not sync local frontend applications list!')
        else:
            new_apps = ', '.join(str(pk) for pk in update_response['new_apps'])
            deprecated_apps = ', '.join(str(pk) for pk in update_response['deactivated_apps'])
            logger.info(f'New apps synced to frontend: [{new_apps}]')
            logger.info(f'Deprecated apps: [{deprecated_apps}]')

    # Fetch the app selection form for session selection
    context['select_application_form'] = forms.SelectApplicationForm()

    # Check if user submitted a form
    if request.method == "POST":

        # Check user actually picked an application
        if 'application' in request.POST:
            current_application = models.Application.objects.get(pk=request.POST['application'])
            context['current_application'] = current_application

            # Check if user submitted using the 'start session' form
            if 'startup' in request.POST:

                logger.info(f'User {request.user.username} starting interactive "{current_application.name}" session')
                api_response = api.start_session(app_id=current_application.pk, dataset_id=load_file.backend_uuid)

                # Prepare regex to parse error string if needed
                check_pattern = re.compile('Failed to create interactive session: Chosen client.*is not available')

                if api_response.is_valid:
                    context['session_in_progress'] = True
                    request.session['app_session_id'] = api_response.body.payload.interactive_session_id

                # else, if the client is busy and there's a session cookie, try to close it
                elif check_pattern.match(api_response.body.error.message) and 'app_session_id' in request.session:
                    logger.warning('Client is busy; attempting to close previous session')

                    app_session_id = request.session['app_session_id']
                    closure_api_response = api.close_session(app_session_id)

                    if not closure_api_response.is_valid:
                        logger.error(f'Could not close blocking session!')

                    # Try again to open the session
                    else:
                        api_response = api.start_session(app_id=current_application.pk, dataset_id=load_file.backend_uuid)

                        if api_response.is_valid:
                            context['session_in_progress'] = True
                            request.session['app_session_id'] = api_response.body.payload.interactive_session_id

                # If no session was opened even after all that, handle the error
                if not 'session_in_progress' in context:
                    logger.error(f'Session failed to start!')
                    messages.warning(request, f'Could not start session!  Check if there is a session of {current_application.name} already running and, if so, close it.')

            # Check if user submitted using the 'end session' form
            elif 'end_session' in request.POST:

                logger.info(f'User {request.user.username} closing active session')

                # If cookie is lost, abort
                if 'app_session_id' not in request.session:
                    logger.warning('No session cookie found!')
                    messages.warning(request, 'Session timed out! Please try again.')
                    return redirect('initialise_workflow')

                app_session_id = request.session['app_session_id']

                # Close the session and fetch the response from the API
                api_response = api.close_session(app_session_id)

                # If session can't be found, abort
                if not api_response.is_valid:
                    logger.error('Could not close session!')
                    messages.warning(request, 'Session information could not be found! Please start again.')
                    return redirect('initialise_workflow')

                session_closure = api_response.body.payload.interactive_sessions[0]

                # If session failed to close for any other reason, abort
                if session_closure.status != 'successful':
                    logger.error('Could not close session!')
                    messages.warning(request, f'Session could not be closed! Check if there is a session of {current_application.name} still running and, if so, close it.')
                    context['session_in_progress'] = True

                # If it was possible to get an outfile from the session via the API
                elif hasattr(session_closure, 'output_dataset_id') and session_closure.output_dataset_id:

                    api_response = api.get_dataset(session_closure.output_dataset_id)

                    if api_response.is_valid:

                        outset_meta = api_response.body.payload.datasets[0]
                        outfile_meta_dict = outset_meta.data_files.additional_properties
                        outfile_meta = next(iter(outfile_meta_dict.values()))

                        # Append disambiguation number to the end of a display filename if needed
                        current_filenames = models.FileMetaData.objects.filter(active=True).values_list('display_filename', flat=True)

                        if outfile_meta.filename in current_filenames:
                            i = 2
                            [new_filename_lead, new_filename_ext] = outfile_meta.filename.split('.')
                            while f'{new_filename_lead}({i}).{new_filename_ext}' in current_filenames:
                                i += 1
                            display_filename = f'{new_filename_lead}({i}).{new_filename_ext}'

                        else:

                            display_filename = outfile_meta.filename

                        # Create record for new file's metadata
                        newfile = models.FileMetaData(
                            filename=outfile_meta.filename,
                            display_filename=display_filename,
                            user=request.user,
                            group=load_file.group,
                            backend_uuid=outset_meta.qcrbox_dataset_id,
                            filetype=outfile_meta.filetype,
                        )
                        newfile.save()

                        # Create record for workflow step
                        newprocessstep = models.ProcessStep(
                            application=current_application,
                            infile=load_file,
                            outfile=newfile,
                        )
                        newprocessstep.save()

                        # Redirect to workflow for new file
                        return redirect('workflow', file_id=newfile.pk)

                else:

                    # If session did not produce output file, issue a warning
                    logger.info('No outfile associated with the session was found.')
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
        if not hasattr(current_file, 'processed_by'):
            break

    # Add results of the prior step finder to the context
    context['prior_steps'] = prior_steps

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

    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            logger.info(f'User {request.user.username} logged in')
            messages.success(request, 'Login Successful: Welcome, '+str(request.user))
            return redirect('landing')

        logger.info(f'User {request.user.username} failed to log in')
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
    logger.info(f'User {username} logged out')
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

            logger.info(f'User {request.user.username} created new user "{new_user.username}"')
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
    p = Paginator(object_list, 13)
    page = request.GET.get('page')

    try:
        objects = p.get_page(page)
    except PageNotAnInteger:
        objects = p.page(1)
    except EmptyPage:
        objects = p.page(p.num_pages)

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
    update_generic().

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

    return update_generic(
        request=request,
        Model=User,
        ModelForm=forms.UpdateUserForm,
        obj_type='User',
        link_suffix='users',
        obj_id=user_id,
        user_is_affiliated=shared_groups.exists(),
    )

@permission_required('qcrbox.edit_users', raise_exception=True)
def delete_user(request, user_id):
    '''A view to handle the deletion of users.  Based on delete_generic().

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

    return delete_generic(
        request=request,
        Model=User,
        obj_type='User',
        link_suffix='users',
        obj_id=user_id,
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
            logger.info(f'User {request.user.username} created new group "{name}"')
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
    p = Paginator(object_list, 13)
    page = request.GET.get('page')

    try:
        objects = p.get_page(page)
    except PageNotAnInteger:
        objects = p.page(1)
    except EmptyPage:
        objects = p.page(p.num_pages)

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
    update_generic().

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

    return update_generic(
        request=request,
        Model=Group,
        ModelForm=forms.GroupForm,
        obj_type='Group',
        link_suffix='groups',
        obj_id=group_id,
        user_is_affiliated=True
    )

@permission_required('qcrbox.global_access', raise_exception=True)
def delete_group(request, group_id):
    '''A view to handle the deletion of groups.  Based on delete_generic().

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

    return delete_generic(
        request=request,
        Model=Group,
        obj_type='Group',
        link_suffix='groups',
        obj_id=group_id,
        user_is_affiliated=True,
    )


# ====================================================
# ========== Data Management related views ===========
# ====================================================

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
    p = Paginator(object_list, 13)
    page = request.GET.get('page')

    try:
        objects = p.get_page(page)
    except PageNotAnInteger:
        objects = p.page(1)
    except EmptyPage:
        objects = p.page(p.num_pages)

    return render(request, 'view_list_generic.html', {
        'objects': objects,
        'type':'Dataset',
        'fields':fields,
        'edit_perms':request.user.has_perm('qcrbox.edit_data'),
        'delete_link':'delete_dataset',
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

    shared_groups = (deletion_data_group in current_user_groups)

    # Check credentials before invoking the generic delete, as API will also need calling
    if shared_groups or request.user.has_perm('qcrbox.global_access'):

        logger.info(f'User {request.user.username} deleting dataset {deletion_data_meta.display_filename}')
        api_response = api.delete_dataset(deletion_data_meta.backend_uuid)

    else:
        raise PermissionDenied

    if not api_response.is_valid:
        logger.error('Could not delete dataset!')
        messages.warning(request, 'API delete request unsuccessful: file not deleted!')
        return redirect('view_datasets')

    try:
        instance = models.FileMetaData.objects.get(pk=dataset_id)

    except models.FileMetaData.DoesNotExist:
        logger.info(f'User {request.user.username} attempted to deactivate non-existent File Metadata (pk={dataset_id})')
        messages.success(request, f'Dataset was deleted succesfully.')
        return redirect('view_datasets')

    # Don't actually delete the local metadata, just flag it as inactive so history can be preserved
    instance.active = False
    instance.save()

    logger.info(f'User {request.user.username} flagged File Metadata "{instance}" as inactive.')
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
        logger.info(f'User {request.user.username} denied permission to download dataset "{download_file_meta.display_filename}" (unaffiliated)')
        raise PermissionDenied

    logger.info(f'User {request.user.username} downloading dataset "{download_file_meta.display_filename}"')
    api_response = api.download_dataset(download_file_meta.backend_uuid)

    if not api_response.is_valid:
        messages.warning(request, 'Could not fetch the requested file!')
        logger.error(f'Could not find requested dataset!')
        return redirect('initialise_workflow')

    data = api_response.body

    # Deliver the file using the filename stored in metadata
    httpresponse = HttpResponse(data)
    httpresponse['Content-Disposition'] = 'attachment; filename='+download_file_meta.display_filename
    return httpresponse


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
