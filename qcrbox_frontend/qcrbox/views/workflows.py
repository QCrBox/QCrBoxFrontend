'''QCrBox Workflows

Module containing the view methods which generate and serve http responses to
the browser when their related url is accessed.

Contains views pertaining to Workflow usage and Session management-related
views.

'''

import logging

from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied

from qcrbox import api, forms, models, utility
from qcrbox import workflow as wf
from qcrbox.plotly_dash import plotly_app                           # pylint: disable=unused-import
from qcrbox.utility import DisplayField, paginate_objects

LOGGER = logging.getLogger(__name__)


@login_required(login_url='login')
def landing(_):
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

    # Set up context with form instances
    context = {
        'loadfile_form':forms.LoadFileForm(user=request.user, auto_id='load-dataset-%s'),
        'newfile_form':forms.UploadFileForm(user=request.user, auto_id='upload-dataset-%s'),
    }

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
                    context,
                )

            file = request.FILES['file']

            # Check the uploaded file is actually a cif.  If not, fail safely
            if str(file)[-4:] != '.cif':
                messages.warning(request, 'Uploaded files must be .cif!')

                return render(
                    request,
                    'initial.html',
                    context,
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
        context,
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

    # Fetch the current file from the file_id passed in url
    load_file = models.FileMetaData.objects.get(pk=file_id)   # pylint: disable=no-member

    # Check the user has permission to view this file
    utility.check_user_view_file_permission(request.user, load_file)

    # Setup context dict to be populated throughout
    context = {'file' : load_file}

    # Get the most recent app list from the API at the start of each workflow, sync the local list
    if not (request.POST and 'application' in request.POST):
        wf.update_apps(request)

    # Fetch the app selection form for session selection
    context['select_command_form'] = forms.SelectCommandForm()

    # Check if user submitted a form
    if request.method == 'POST':

        # Check if a 'end calculation' command was issued
        if 'end_calculation' in request.POST:
            wf.cancel_calculation(request)
            return redirect('workflow', file_id=file_id)

        # Check user actually picked a command
        if 'command' in request.POST:
            comm_id = request.POST['command']
            current_command = models.AppCommand.objects.get(pk=comm_id) # pylint: disable=no-member
            context['current_command'] = current_command
            context['command_form'] = forms.CommandForm(
                command=current_command,
                dataset=load_file,
            )

            # Deal with starting/ending sessions and/or starting/polling calculations
            work_status = wf.handle_command(request, current_command, load_file)

            if work_status.outfile_id:
                return redirect('workflow', file_id=work_status.outfile_id)

            if work_status.session_is_open:
                context['session_in_progress'] = True

            if work_status.calc_is_pending:
                context['calculation_in_progress'] = True
                context['refresh_time'] = settings.AUTO_REFRESH_TIME


    # Populate the workflow diagram with all steps leading up to the current file
    context['prior_steps'] = wf.get_file_history(load_file)

    # Fetch the interactive session ID to allow it to be shown on page
    if 'app_session_id' in request.session:
        context['app_session_id'] = request.session['app_session_id']
    else:
        context['app_session_id'] = None

    return render(request, 'workflow.html', context)


# A separate view to handle the auto-refreshing page when waiting for calc to finish
@login_required(login_url='login')
def workflow_pending(request, file_id, command_id):
    '''A view to handle generating the correct context to display the auto-
    refreshing 'holding zone' while waiting for a non-interactive calculation
    to run, without having to constantly resubmit forms. 

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - file_id(int): the Frontend db primary key of the dataset being used
            for this workflow.
    - command_id(int): the Frontend db primary key of the command currently
            being run.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    load_file = models.FileMetaData.objects.get(pk=file_id)   # pylint: disable=no-member
    command = models.AppCommand.objects.get(pk=command_id)    # pylint: disable=no-member

    if 'end_calculation' in request.POST:
        wf.cancel_calculation(request)
        return redirect('workflow', file_id=file_id)

    utility.check_user_view_file_permission(request.user, load_file)
    work_status = wf.poll_calculation(request, load_file, command)

    if work_status.outfile_id:
        return redirect('workflow', file_id=work_status.outfile_id)

    context = {
        'file' : load_file,
        'current_command' : command,
        'calculation_in_progress' : True,
        'refresh_time' : settings.AUTO_REFRESH_TIME,
        'prior_steps' : wf.get_file_history(load_file),
    }

    return render(request, 'workflow.html', context)


# Edit Users permission is used as a proxy for Group Manager status
@login_required(login_url='login')
def view_sessions(request):
    '''A view to handle generating and rendering the 'view sessions' page which
    displays active Sessions and allows them to be terminated.  The contents of
    this page assume the user has Group Manager status, but the Sessions visible
    are filtered based on the request user's groups and are paginated.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    fields = [
        DisplayField('App', 'command__app', is_header=True),
        DisplayField('Command', 'command'),
        DisplayField('Invoked By', 'user'),
        DisplayField('At Time', 'start_time'),
        ]

    object_list = models.SessionReference.objects.all()                 # pylint: disable=no-member

    # If a user can view unaffiliated data, they can view it all
    if request.user.has_perm('qcrbox.global_access'):
        pass
    elif request.user.has_perm('qcrbox.edit_users'):
        object_list = object_list.filter(user__groups__in=request.user.groups.all())
    else:
        object_list = object_list.filter(user=request.user)

    object_list = object_list.order_by('start_time')
    page = request.GET.get('page')

    objects = paginate_objects(object_list, page)

    return render(request, 'view_list_generic.html', {
        'objects': objects,
        'type':'Session',
        'fields':fields,
        'kill_link':'kill_session',
    })

@login_required(login_url='login')
def kill_session(request, sessionref_id):
    '''A view to handle the manual killing of sessions via the group
    admin-level 'View Sessions' panel.  Attempts to close a session
    with an API call; if succesful (or the call fails with a 404),
    also deletes the related SessionReference object.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - sessionref_id(int): the Frontend db primary key of the SessionReference
            which refers to the session/calculation to be killed.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.
    '''

    # Fetch the session reference object
    session_ref = models.SessionReference.objects.get(pk=sessionref_id) # pylint: disable=no-member

    # Run some last minute permission checks to ensure the user should be allowed to do this
    if request.user.has_perm('qcrbox.global_access'):
        pass
    elif request.user.has_perm('edit_users'):
        if not (session_ref.user.groups.all() & request.user.groups.all()).exists():
            raise PermissionDenied
    else:
        if session_ref.user != request.user:
            raise PermissionDenied

    # Fetch the relevant getters and closers for whether the command is interactive or not
    if session_ref.command.interactive:
        api_get = api.get_session
        api_kill = api.close_session
        def check_inactive(_):
            return False

    else:
        api_get = api.get_calculation
        api_kill = api.cancel_calculation
        def check_inactive(get_response):
            return get_response.body.payload.calculations[0].status in ('successful', 'failed')

    get_response = api_get(session_ref.session_id)

    # See if the session can be found
    if not get_response.is_valid:
        if get_response.body.error.code == 404:
            # If the related session doesn't actually exist, just quietly delete the reference
            session_ref.delete()
            messages.info(
                request,
                'Session ended successfully',
            )
        else:
            messages.warning(
                request,
                'Could not kill session!',
            )

    # Is session already ended, then again quietly delete the frontend reference
    elif check_inactive(get_response):
        session_ref.delete()
        messages.info(
            request,
            'Session ended successfully',
        )

    # If the session is found, try to close it
    else:
        api_response = api_kill(session_ref.session_id)
        if api_response.is_valid:
            session_ref.delete()
            messages.info(
                request,
                'Session ended successfully',
            )
        else:
            messages.warning(
                request,
                'Could not kill session!',
            )

    return redirect('view_sessions')
