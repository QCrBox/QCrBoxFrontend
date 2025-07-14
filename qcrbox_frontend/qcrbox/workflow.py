'''workflow.py: a module to contain functionality pertaining to the main
workflow and initialise_workflow views which contains the majority of QCrBox
Frontend's functionality.  Refactored here for readability.

'''

import logging
import re

from django.contrib import messages

from . import api
from . import models
from . import utility

LOGGER = logging.getLogger(__name__)

def save_dataset_metadata(request, api_response, group, infile=None, application=None):
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
    - application(Application, optional): the Application data corresponding
            to the application used in the Interactive Session which generated
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

    if application and infile:
        # Create record for workflow step
        newprocessstep = models.ProcessStep(
            application=application,
            infile=infile,
            outfile=newfile,
        )
        newprocessstep.save()

    # Return the new file instance
    return newfile


def create_session_references(request, api_response, application):
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
    - application(Application): the Application data corresponding
            to the application used to start the Interactive Session.

    '''

    session_id = api_response.body.payload.interactive_session_id

    # set browser cookie
    request.session['app_session_id'] = session_id

    session_reference = models.SessionReference(
        user=request.user,
        application=application,
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

    # clear cookie
    request.session['app_session_id'] = None

    session = models.SessionReference.objects.get(session_id=session_id)# pylint: disable=no-member
    session.delete()


def start_session(request, infile, application):
    '''Given an application and an input FileMetaData object, attempt to start
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

    LOGGER.info(
        'User %s starting interactive "%s" session',
        request.user.username,
        application.name,
    )
    api_response = api.start_session(
        app_id=application.pk,
        dataset_id=infile.backend_uuid,
    )

    if api_response.is_valid:
        create_session_references(request, api_response, application)
        return True

    # else, if the client is busy and there's a session cookie, try to close it
    LOGGER.warning('Client is busy; attempting to close previous session')

    current_sessions = models.SessionReference.objects                  # pylint: disable=no-member
    relevant_sessions = current_sessions.filter(application=application)

    if 'app_session_id' in request.session and request.session['app_session_id']:
        app_session_id = request.session['app_session_id']

    elif relevant_sessions.exists():
        app_session_id = relevant_sessions.first().session_id
        LOGGER.warning('No cookie found; fetching session ID from reference db')

    else:
        LOGGER.error('Could not find cookie or reference to blocking session!')
        messages.warning(
            request,
            f'Could not start session of {application.name}!  Client seems'
            f'to be busy.'
        )
        return False

    closure_api_response = api.close_session(app_session_id)

    if not closure_api_response.is_valid:
        LOGGER.error('Could not close blocking session!')

    # Try again to open the session
    else:
        # clear any dangling references to the old session
        clear_session_references(request, session_id=app_session_id)

        api_response = api.start_session(
            app_id=application.pk,
            dataset_id=infile.backend_uuid
        )

        if api_response.is_valid:
            create_session_references(request, api_response, application)
            return True

    # If no session was opened even after all that, handle the error
    LOGGER.error('Session failed to start!')
    messages.warning(
        request,
        f'Could not start session!  Check if there is a session of'
        f'{application.name} already running and, if so, close it.'
    )
    return False


def close_session(request, infile, application):
    '''Attempt to close the session corresponding to the session_id stored in
    the user's browser cookies.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to the view containing this workflow.
    - infile(FileMetaData): the FileMetaData object corresponding to the file
            being used for this Interactive Session.  Only used for generating
            logs and user messages.
    - application(Application): the Application data corresponding
            to the application used in this Interactive Session.  Only used for
            generating logs and user messages.

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
    if 'app_session_id' not in request.session:
        LOGGER.error('No session cookie found!')
        messages.warning(request, 'Session timed out! Please try again.')
        return None

    app_session_id = request.session['app_session_id']

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
            f'{application.name} did not close properly!  Make sure to close the application in '
            'the new browser tab before clicking End Session in order to avoid loss of data.'
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
                application=application,
            )

            return newfile

    # If session did not produce output file, issue a warning
    LOGGER.info('No outfile associated with the session was found.')
    messages.info(request, 'No output was produced in the interactive session.')

    return 'NO_OUTPUT'


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
