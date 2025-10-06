'''workflow.py: a module to contain functionality pertaining to the main
workflow and initialise_workflow views which contains the majority of QCrBox
Frontend's functionality.  Refactored here for readability.

'''

import logging
import time

from django.contrib import messages

from qcrbox import api
from qcrbox import forms
from qcrbox import models
from qcrbox import utility

LOGGER = logging.getLogger(__name__)

class WorkStatus():
    '''A simple object to compactly return all salient information on
    the status of the current session/command to the workflow

    '''

    def __init__(self, session_is_open=False, calc_is_pending=False, outfile_id=None):
        '''Store whether the command has an associated active session,
        whether a calculation is pending, and whether an outfile has been
        created.

        '''

        self.session_is_open = session_is_open
        self.calc_is_pending = calc_is_pending
        self.outfile_id = outfile_id


def save_dataset_metadata(request, api_response, group, infile=None, command=None, params='{}'):
    '''Given a succesful upload of data to the backend, take the API response
    returned from that upload and create a Frontend FileMetaData object to
    refer to the uploaded dataset.  If the new file is the output of an
    Interactive Session, also save information on the session as a ProcessStep
    instance.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to the view containing this workflow.
    - api_response(api.Response): an api.Response object containing the
            response from the API on saving a dataset to the backend, and
            a boolean flag indicating whether the response indicated success
    - group(Group): The group to which the new dataset should be allocated
    - infile(FileMetaData, optional): the FileMetaData object corresponding
            to the file from which this file was generated, e.g. through
            Interactive Session.  Set blank to indicate that this file has
            no ancestor, i.e. it was created by direct upload.
    - command(AppCommand, optional): the AppCommand data corresponding
            to the application command used in the session which generated
            this dataset, if applicable.

    Returns:
    - newfile(FileMetaData): the newly created FileMetaData object.

    '''

    outset_meta = api_response.body.payload.datasets[0]
    outfile_meta = next(iter(outset_meta.data_files.additional_properties.values()))

    # Append disambiguation number to the end of a display filename if needed
    curr_files = models.FileMetaData.objects.filter(active=True)        # pylint: disable=no-member
    curr_filenames = curr_files.values_list('display_filename', flat=True)

    if outfile_meta.filename in curr_filenames:
        i = 2
        [new_filename_lead, new_filename_ext] = outfile_meta.filename.split('.')
        while f'{new_filename_lead}({i}).{new_filename_ext}' in curr_filenames:
            i += 1
        display_filename = f'{new_filename_lead}({i}).{new_filename_ext}'

    else:

        display_filename = outfile_meta.filename

    # Create record for new file's metadata
    newfile = models.FileMetaData(
        filename=outfile_meta.filename,
        display_filename=display_filename,
        user=request.user,
        group=group,
        backend_uuid=outset_meta.qcrbox_dataset_id,
        filetype=outfile_meta.filetype,
    )
    newfile.save()

    LOGGER.info(
        'Metadata for file %s saved, backend_uuid=%s',
        display_filename,
        outset_meta.qcrbox_dataset_id,
    )

    if command and infile:
        # Create record for workflow step
        newprocessstep = models.ProcessStep(
            command=command,
            infile=infile,
            outfile=newfile,
            parameters=params,
        )
        newprocessstep.save()

    # Return the new file instance
    return newfile


def create_session_references(request, api_response, command):
    '''When starting a new session, this function can be invoked to create two
    references to that session; firstly, as a browser-side cookie containing
    the backend session_id and, secondly, a temporary SessionReference record
    in the Frontend db pointing to that session in the event that the
    cookie is lost for any reason.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to the view containing this workflow.
    - api_response(api.Response): an api.Response object containing the
            response from the API on starting an Interactive Session, and
            a boolean flag indicating whether the response indicated success.
            Only used to fetch the session_id.
    - command(AppCommand): the AppCommand data corresponding
            to the command used to start the Interactive Session.

    '''

    session_id = api_response.body.payload.calculation_id

    # set browser cookie
    request.session['session_id'] = session_id

    session_reference = models.SessionReference(
        user=request.user,
        command=command,
        session_id=session_id,
    )
    session_reference.save()


def clear_session_references(request, session_id):
    '''When closing a session, this function can be invoked to clear the
    browser cookie referring to it and delete the SessionReference record
    in the Frontend db.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to the view containing this workflow.
    - session_id(str): the ID used to refer to this session in the backend.

    '''

    # remove browser cookie
    request.session['session_id'] = None

    session = models.SessionReference.objects.get(session_id=session_id)# pylint: disable=no-member
    session.delete()


def start_session(request, command, arguments):
    '''Given a command and an input FileMetaData object, attempt to start
    a new Interactive Session, handling errors, messaging and logging as
    appropriate.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to the view containing this workflow.
    - infile(FileMetaData): the FileMetaData object corresponding to the file
            being used for this Interactive Session.
    - application(Application, optional): the Application data corresponding
            to the application used in this Interactive Session.

    Returns:
    - session_created(bool): a boolean which indicates whether a new session
            was successfully started.

    '''

    application = command.app

    LOGGER.info(
        'User %s starting interactive "%s" session',
        request.user.username,
        application.name,
    )
    api_response = api.send_command(command.pk, arguments)

    if api_response.is_valid:
        create_session_references(request, api_response, command)
        return True
    startup_error = api_response.body.error.message

    # else, if the client is busy and there's a session cookie, try to close it
    LOGGER.warning('Client is busy; attempting to close previous session')

    current_sessions = models.SessionReference.objects                  # pylint: disable=no-member
    relevant_sessions = current_sessions.filter(command__app=command.app)

    if relevant_sessions.exists():
        if relevant_sessions.exclude(user=request.user).exists():
            messages.warning(
                request,
                f'Could not start session of {application.name}: currently in use by another user!',
            )
            return False
        killed_a_session = kill_sessions(request, sessions=relevant_sessions)

    else:
        LOGGER.error('Could not find reference to blocking session!')
        messages.warning(
            request,
            f'Could not start session of {application.name}! {startup_error}.'
        )
        return False

    if not killed_a_session:
        LOGGER.error('Could not close blocking session!')
        messages.warning(
            request,
            f'Could not start session of {application.name}! Could not close blocking session.'
        )

    # Try again to open the session
    else:
        api_response = api.send_command(command.pk, arguments)

        if api_response.is_valid:
            create_session_references(request, api_response, command)
            return True

        # If response wasnt valid, let the user know why
        messages.warning(
            request,
            f'Could not start session!  Returned error: '
            f'{application.name}'
        )

    # If no session was opened even after all that, handle the error
    LOGGER.error('Session failed to start!')
    return False


def close_session(request, infile, command):
    '''Attempt to close the session corresponding to the session_id stored in
    the user's browser cookies.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to the view containing this workflow.
    - infile(FileMetaData): the FileMetaData object corresponding to the file
            being used for this Interactive Session.  Only used for generating
            logs and user messages.
    - command(AppCommand): the AppCommand data corresponding to the application
            command used in this Interactive Session.  Only used for generating
            logs and user messages.

    Returns:
    - out_file(FileMetaData or str or None): contains information on the status
            of the session being closed, and information on the output file if
            any.  A value of None indicates the session was not successfully
            closed.  A string value of 'NO_OUTPUT' indicates that the session
            was closed succesfully but returned no output file.  Otherwise,
            returns the FileMetaData object corresponding to the new file
            created by closing the session.

    '''

    LOGGER.info(
        'User %s closing active session',
        request.user.username,
    )

    # If cookie is lost, abort
    if 'session_id' not in request.session:
        LOGGER.error('No session cookie found!')
        messages.warning(request, 'Session timed out! Please try again.')
        return None

    app_session_id = request.session['session_id']

    # Close the session and fetch the response from the API
    api_response = api.close_session(app_session_id)

    # If session can't be found, abort
    if not api_response.is_valid:
        LOGGER.error('Could not close session!')
        messages.warning(
            request,
            'Session information could not be found! Please start again.'
        )
        return None

    session_closure = api_response.body.payload.interactive_sessions[0]
    clear_session_references(request, session_id=app_session_id)

    # If session failed for any reason, log it but continue
    if session_closure.status != 'successful':
        LOGGER.warning('Session force-closed!')
        messages.warning(
            request,
            f'{command.app.name} did not close properly!  Make sure to close the '
            'application in the new browser tab before clicking End Session in order to avoid '
            'loss of data.'
        )

    # If it was possible to get an outfile from the session via the API
    if (hasattr(session_closure, 'output_dataset_id') and session_closure.output_dataset_id):

        api_response = api.get_dataset(session_closure.output_dataset_id)

        if api_response.is_valid:

            newfile = save_dataset_metadata(
                request,
                api_response,
                infile.group,
                infile=infile,
                command=command,
            )

            return newfile

    # If session did not produce output file, issue a warning
    LOGGER.info('No outfile associated with the session was found.')
    messages.info(request, 'No output was produced in the interactive session.')

    return 'NO_OUTPUT'


def kill_sessions(request, sessions):
    '''Given a queryset of SessionReference objects, attempt to close each
    session its session_id, purging the corresponding SessionReference for
    each succesful closure.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to the view containing this workflow.
    - sessions(QuerySet): a queryset of SessionReference objects which
            are to be force-closed.

    Returns:
    - at_least_one_closed(bool): a Boolean which states whether the kill
            command resulted in any change to the db/filestore (i.e.
            whether at least one closure was succesfully performed)

    '''

    at_least_one_closed = False

    for session in sessions:

        closure_api_response = api.close_session(session.session_id)

        if closure_api_response.is_valid:
            at_least_one_closed = True
            clear_session_references(request, session.session_id)
        else:
            LOGGER.error(
                'Could not close blocking session [%s]!',
                session.session_id
            )

    return at_least_one_closed


def invoke_command(request, command, arguments):
    '''Given an command and a dict of command arguments, instruct
    the API to invoke the command to start a calculation in the backend, 
    handling errors, messaging and logging as appropriate.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to the view containing this workflow.
    - command(AppCommand): the AppCommand object corresponding to the command
            being used for this Session.
    - arguments(dict): the additional kwargs to be passed to the API when
            invoking the command.

    Returns:
    - calculation_created(bool or str): the calculation_id of the calculation
            if it was invoked succesfully, otherwise False.

    '''

    LOGGER.info(
        'User %s invoking command "%s" from app "%s"',
        request.user.username,
        command.app.name,
        command.name,
    )
    api_response = api.send_command(command.pk, arguments)

    if api_response.is_valid:
        create_session_references(request, api_response, command)
        return api_response.body.payload.calculation_id
    startup_error = api_response.body.error.message

    # else, if the client is busy and there's an open session of the same app, try to close it
    LOGGER.warning('Client is busy; attempting to kill blocking calculation session')
    current_sessions = models.SessionReference.objects                  # pylint: disable=no-member
    relevant_sessions = current_sessions.filter(command__app=command.app)

    if relevant_sessions.exists():
        if relevant_sessions.exclude(user=request.user).exists():
            messages.warning(
                request,
                f'Could not start session of {command.app.name}: currently in use by another user!',
            )
            return False
        killed_a_session = kill_sessions(request, sessions=relevant_sessions)

    else:
        LOGGER.error('Could not find reference to blocking session!')
        messages.warning(
            request,
            f'Could not invoke command of {command.name}! {startup_error}.'
        )
        return False

    if not killed_a_session:
        LOGGER.error('Could not cancel blocking calculation!')
        messages.warning(
            request,
            f'Could not start session of {command.app.name}! Could not close blocking session.'
        )

    # Try again to open the session
    else:
        api_response = api.send_command(command.pk, arguments)

        if api_response.is_valid:
            create_session_references(request, api_response, command)
            return api_response.body.payload.calculation_id

    # If no session was opened even after all that, handle the error
    LOGGER.error('Calculation failed to start!')
    messages.warning(
        request,
        f'Could not invoke command! {startup_error}.'
    )
    return False


def update_apps(request):
    '''A wrapper around the utility.py update_applications() method to handle
    logging and user message functionality whether the app update succeeded or
    failed'''

    update_response = utility.update_applications()
    if not update_response:
        messages.warning(request, 'Warning: could not update applications list!')
        LOGGER.warning('Could not sync local frontend applications list!')
    else:
        new_apps = ', '.join(str(pk) for pk in update_response['new_apps'])
        deprecated_apps = ', '.join(str(pk) for pk in update_response['deactivated_apps'])
        reactivated_apps = ', '.join(str(pk) for pk in update_response['reactivated_apps'])

        LOGGER.info(
            'New apps synced to frontend: [%s]',
            new_apps,
        )
        LOGGER.info(
            'Deprecated apps: [%s]',
            deprecated_apps,
        )
        LOGGER.info(
            'Reactivated apps: [%s]',
            reactivated_apps,
        )


def get_file_history(infile):
    '''Given a FileMetaData object, recursively fetch the process that created
    it and the file given as input to that process (if applicable), to build
    up a full linear ancestry of the related dataset.

    Parameters:
    - infile(FileMetaData): the FileMetaData object corresponding the dataset
            which is having its ancestry constructed.

    Returns:
    - ancestry(list): an ordered list of ProcessStep objects representing the
            creation history of the infile.  Ordered chronologically from
            early to late.

    '''

    prior_steps = []
    current_file = infile

    # While working on a step with a creation history...
    while current_file.processed_by.all():
        prior_step = current_file.processed_by.first()
        prior_steps = [prior_step] + prior_steps

        # Move one step back if possible
        current_file = prior_step.infile

        # Failsafe for if the prior step is malformed
        if not hasattr(current_file, 'processed_by'):
            break

    return prior_steps


def fetch_calculation_result(request, infile, command):
    '''Attempt to fetch the results of a non-interactive calculation
    corresponding to the calculation_id stored in the user's browser cookies,
    or return a flag if the calc is still pending.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to the view containing this workflow.
    - infile(FileMetaData): the FileMetaData object corresponding to the file
            being used for this Calculation.  Only used for generating
            logs and user messages.
    - command(AppCommand): the AppCommand data corresponding to the application
            command used in this Interactive Session.  Only used for generating
            logs and user messages.

    Returns:
    - out_file(FileMetaData or str or None): contains information on the status
            of the session being closed, and information on the output file if
            any.  A value of None indicates the calculation was not successfully
            completed.  A string value of 'PENDING' indicates that the
            calculation is still running.  Otherwise, returns the FileMetaData
            object corresponding to the new file created by the calculation.

    '''

    # If cookie is lost, abort
    if 'session_id' not in request.session:
        LOGGER.error('No calculation cookie found!')
        messages.warning(request, 'Calculation reference timed out! Please try again.')
        return None

    calculation_id = request.session['session_id']

    # Fetch the calculation status from the API
    api_response = api.get_calculation(calculation_id)

    # If calculation can't be found, abort
    if not api_response.is_valid:
        LOGGER.error('Calculation error!')
        messages.warning(
            request,
            'Calculation could not be found! Please start again.'
        )
        return None

    calculation = api_response.body.payload.calculations[0]

    if calculation.status in ('submitted', 'running'):
        return 'PENDING'

    if calculation.status == 'successful':
        api_response = api.get_dataset(calculation.output_dataset_id)
        clear_session_references(request, session_id=calculation_id)

        if api_response.is_valid:

            newfile = save_dataset_metadata(
                request,
                api_response,
                infile.group,
                infile=infile,
                command=command,
                params=calculation.command_arguments.additional_properties,
            )

            return newfile

        messages.info(
            request,
            f'{command.name} produced no output.'
        )
        return None

    messages.warning(
        request,
        f'{command.name} did not execute successfully.'
    )

    LOGGER.info(
        'Calculation returned status: %s',
        calculation.status,
    )
    return None


def cancel_calculation(request):
    '''Fetch the current session cookie from the user's browser, and instruct
    API to close the corresponding calculation

    '''

    # If cookie is lost, abort
    if 'session_id' not in request.session:
        LOGGER.error('No calculation cookie found!')
        messages.warning(request, 'Calculation reference timed out! Could not cancel session.')
        return

    api.cancel_calculation(request.session['session_id'])
    clear_session_references(request, session_id=request.session['session_id'])


def poll_calculation(request, infile, command):
    '''Poll a running calculation (based on the calc_id stored in the user's
    browser cookies), fetches and saves the result if its ready, and returns
    a status which contains the outfile_id if present

    '''

    outfile = fetch_calculation_result(
        request,
        infile,
        command,
    )

    if outfile == 'PENDING':
        return WorkStatus(calc_is_pending=True)
    if outfile is None:
        return WorkStatus(calc_is_pending=False)
    return WorkStatus(outfile_id=outfile.pk)


def handle_command(request, command, infile):
    '''A function to handle the internal logic of launching commands, ending
    sessions, polling active calculations to see if outfiles have been
    produced, and returning outfiles when they exist.

    '''

    # Check if user submitted using the 'start session' form
    if 'startup' in request.POST:

        # Check the form is valid
        submitted_form = forms.CommandForm(
            request.POST,
            command=command,
            dataset=infile,
        )
        if not submitted_form.is_valid():
            messages.warning(request, 'Input values not valid: try again!')
            return WorkStatus()

        # Fetch the params from the POST data
        cps = command.parameters
        expected_params = cps.values_list('name',flat=True)
        params = {p:request.POST[p] for p in request.POST if p in expected_params}

        # Also fetch any uploaded files
        auxfiles = {f:request.FILES[f] for f in request.FILES if f in expected_params}

        # Populate any missing bool params with 'False' (default includes no POST data for
        # unchecked checkbox widgets)
        for i in cps.filter(dtype='bool').values_list('name',flat=True):

            if not i in params:
                params[i] = False

        # Format any params related to infiles to specify they should be fetched by ID
        for i in cps.filter(dtype='QCrBox.cif_data_file').values_list('name',flat=True):

            try:
                params[i] = {'data_file_id': params[i]}

            except KeyError:
                messages.warning(request, f'No file provided for "{i}"')
                return WorkStatus()

        # Handle aux files uploaded as part of the form
        for i in cps.filter(dtype='QCrBox.data_file').values_list('name',flat=True):
            try:
                # Attempt to upload dataset via the API
                api_response = api.add_file_to_dataset(auxfiles[i], infile.backend_uuid)

                if not api_response.is_valid:

                    LOGGER.error(
                        'File "%s" failed to upload!',
                        str(auxfiles[i]),
                    )

                    messages.warning(request, f'File {auxfiles[i]} failed to upload!')

                    return WorkStatus()

                # Fetch the new file ID from the API response message
                aux_file_id = api_response.body.payload.appended_file.qcrbox_file_id

                # Add the newly uploaded aux file's ID to the params list
                params[i] = {'data_file_id': aux_file_id}

            except KeyError:
                messages.warning(request, f'No file provided for "{i}"')
                return WorkStatus()

        # Sanitise any arguments which dictate output filenames on the file system
        output_dtypes = ('QCrBox.output_path','QCrBox.output_cif')
        for i in cps.filter(dtype__in=output_dtypes).values_list('name',flat=True):
            params[i] = params[i].replace('/','_')

        # If the command corresponds to an interactive session, launch it
        if command.interactive:

            open_session = start_session(
                request,
                command,
                params,
            )

            if open_session:
                return WorkStatus(session_is_open=True)


        # Otherwise, launch the command with any user-given args
        else:

            active_calc = invoke_command(
                request,
                command,
                params,
            )

            if active_calc:
                # Add a brief pause here to allow for short commands to
                # execute without entering the workflow holding pattern
                time.sleep(1)

                # Poll the calculation to see if its ready
                return poll_calculation(request, infile, command)

            return WorkStatus(calc_is_pending=False)


    # Check if user submitted using the 'end session' form
    elif 'end_session' in request.POST:

        outfile = close_session(
            request,
            infile,
            command,
        )

        if not outfile:
            return WorkStatus(session_is_open=True)
        if outfile != 'NO_OUTPUT':
            return WorkStatus(outfile_id=outfile.pk)

    return WorkStatus()
