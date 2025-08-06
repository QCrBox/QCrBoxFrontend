'''QCrBox API Interface

A collection of methods which deal with making calls to the QCrBox API client
and parsing the responses of these calls.

All methods in this module return a Response object containing the response to
the relevant API call and a Boolean flag denoting whether that call was
successful.

'''

import logging

from qcrboxapiclient.api.applications import (
    list_applications,
)
from qcrboxapiclient.api.commands import invoke_command
from qcrboxapiclient.api.datasets import (
    create_dataset,
    delete_dataset_by_id,
    download_dataset_by_id,
    get_dataset_by_id,
)
from qcrboxapiclient.api.interactive_sessions import (
    close_interactive_session,
    create_interactive_session_with_arguments,
    get_interactive_session_by_id,
)
from qcrboxapiclient.client import Client
from qcrboxapiclient.models import (
    CreateDatasetBody,
    CreateInteractiveSessionParameters,
    CreateInteractiveSessionParametersArguments,
    InvokeCommandParameters,
    InvokeCommandParametersArguments,
    QCrBoxErrorResponse,
)
from qcrboxapiclient.types import File

from django.conf import settings
from . import models

LOGGER = logging.getLogger(__name__)

# Set the string length above which non-error API responses will be truncated in the logs
MAX_LENGTH_API_LOG = settings.MAX_LENGTH_API_LOG

# Utility class for returning API responses / errors

class Response():
    '''A class to package any API response with a boolean flag, allowing
    modules and methods upstream of this to be fully agnostic to the
    structure of specific API responses when determining if an API response
    was successful.

    This is essentially just a simple wrapper around an API object, and has
    two important attributes:
    - body: the raw API response object this is a wrapper around
    - is_valid: a Boolean flag to denote whether the API call was deemed
            successful

    '''

    def __init__(self, body=None):
        '''Create a Response object from a raw API response.

        Parameters:
        - body(QCrBoxResponse or similar): the raw API response to be wrapped.

        '''

        self.body = body

        if isinstance(self.body, QCrBoxErrorResponse):
            # If the upload fails, give response an error flag, log it
            LOGGER.error(
                'Error response from API: %s',
                self.body,
            )
            self.is_valid = False

        else:
            # Truncate the API response to sent to the logger if its a success
            logtext = str(self.body)
            if len(logtext) > MAX_LENGTH_API_LOG:
                logtext = logtext[:MAX_LENGTH_API_LOG-2]+' ... '+logtext[-2:]
            LOGGER.info(
                'Response from API: %s',
                logtext,
            )
            self.is_valid = True


# ==========================================
# ========= API functionality here =========
# ==========================================

def get_client():
    '''A function to return an API client object pointing to the API base URL
    set in settings.py

    '''

    client = Client(base_url=settings.API_BASE_URL)
    return client


# ----- Basic API I/O Functionality -----

def upload_dataset(im_file):
    '''Take a django InMemoryFile, prepare it, then send to the API to upload
    to the backend

    Parameters:
    - im_file(InMemoryFile): a byte-like file object stored in memory after
            being uploaded by a user via the file upload form.

    '''

    client = get_client()
    file_bytes = im_file.file
    file_name = str(im_file)

    payload_file = File(file_bytes, file_name)
    upload_payload = CreateDatasetBody(payload_file)

    LOGGER.info('API call: create_dataset')
    raw_response = create_dataset.sync(client=client, body=upload_payload)

    return Response(raw_response)


def download_dataset(dataset_id):
    '''Fetch a datafile from the backend and return its contents to be parsed
    elsewhere for the user to download

    Parameters:
    - dataset_id(str): the backend ID of the dataset to be downloaded
            (equivalent to the backend_uuid attribute of the frontend's
            FileMetaData Model)

    '''

    client = get_client()

    LOGGER.info(
        'API call: download_dataset_by_id, id=%s',
        dataset_id,
    )
    raw_response = download_dataset_by_id.sync(client=client, id=dataset_id)

    return Response(raw_response)


def delete_dataset(dataset_id):
    '''Instruct the backend to delete a dataset.

    Parameters:
    - dataset_id(str): the backend ID of the dataset to be deleted (equivalent
            to the backend_uuid attribute of the frontend's FileMetaData
            Model)

    '''

    client = get_client()

    LOGGER.info(
        'API call: delete_dataset_by_id, id=%s',
        dataset_id,
    )
    raw_response = delete_dataset_by_id.sync(id=dataset_id, client=client)

    return Response(raw_response)


def get_dataset(dataset_id):
    '''Fetch a dataset from the backend by ID and return its backend metadata

    Parameters:
    - dataset_id(str): the backend ID of the dataset to be fetched (equivalent
            to the backend_uuid attribute of the frontend's FileMetaData
            Model)

    '''

    client = get_client()

    LOGGER.info(
        'API call: get_dataset_by_id, id=%s',
        dataset_id,
    )
    raw_response = get_dataset_by_id.sync(client=client, id=dataset_id)

    return Response(raw_response)


# ----- Session Functionality -----

def start_session(app_id, dataset_id):
    '''Command the API to start an Interactive Session using a given
    Application and Dataset.

    Parameters:
    - app_id(int): the primary key of the Application to be used as stored on
            the frontend database.
    - dataset_id(str): the backend ID of the dataset to be fetched (equivalent
            to the backend_uuid attribute of the frontend's FileMetaData
            Model)

    '''

    client = get_client()

    # Get relevant metadata instances from local db
    app = models.Application.objects.get(pk=app_id)                     # pylint: disable=no-member
    dataset_objs = models.FileMetaData.objects                          # pylint: disable=no-member
    dataset_metadata = dataset_objs.get(backend_uuid=dataset_id)

    # Sessions are started with a data_file_id (not a dataset_id), so need to fetch that ID from
    # a dataset
    get_response = get_dataset(dataset_id)

    # Check a dataset was actually found
    if not get_response.is_valid:
        return get_response

    # Get the associated data_file's ID
    dataset = get_response.body.payload.datasets[0]
    datafile_id = dataset.data_files[dataset_metadata.filename].qcrbox_file_id

    # Set up arguments
    arguments = CreateInteractiveSessionParametersArguments.from_dict(
        {'input_file': {'data_file_id': datafile_id}}
    )
    create_session = CreateInteractiveSessionParameters(app.slug, app.version, arguments)

    # Initialise session
    LOGGER.info('API call: create_interactive_session_with_arguments')
    raw_response = create_interactive_session_with_arguments.sync(
        client=client,
        body=create_session,
    )

    return Response(raw_response)

def get_session(session_id):
    '''Get the metadata of an Interactive Session

    Parameters:
    - session_id(str): the backend ID for the session to be fetched

    '''

    client = get_client()

    LOGGER.info(
        'API call: get_interactive_session_by_id, id=%s',
        session_id,
    )
    raw_response = get_interactive_session_by_id.sync(client=client, id=session_id)

    return Response(raw_response)

def close_session(session_id):
    '''Command the API to close an Interactive Session.

    Parameters:
    - session_id(str): the backend ID for the session to be closed

    '''

    client = get_client()

    LOGGER.info(
        'API call: close_interactive_session, id=%s',
        session_id,
    )
    raw_response = close_interactive_session.sync(client=client, id=session_id)

    return Response(raw_response)


# ----- Command functionality -----

def send_command(command_id, parameters):

    client = get_client()

    command = models.AppCommand.objects.get(pk=command_id)              # pylint: disable=no-member

    arguments = InvokeCommandParametersArguments.from_dict(parameters)

    create_session = InvokeCommandParameters(
        command.app.slug,
        command.app.version,
        command.name,
        arguments,
    )

    LOGGER.info(
        'API call: invoke_command, app=%s %s, command=%s, arguments=%s',
        command.app.slug,
        command.app.version,
        command.name,
        arguments,
    )

    raw_response = invoke_command.sync(client=client, body=create_session)

    return Response(raw_response)


# ----- Fetching Application Metadata -----

def get_applications():
    '''Fetch a list of currently installed QCrBox tools and return config
    information such as the port they are accessed via.

    Parameters:
    - None

    '''

    client = get_client()

    LOGGER.info('API call: list_applications')
    raw_response = list_applications.sync(client=client)

    return Response(raw_response)
