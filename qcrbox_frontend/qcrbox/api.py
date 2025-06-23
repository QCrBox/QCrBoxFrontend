import logging

from qcrboxapiclient.api.applications import (
    list_applications,
)
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
    CreateInteractiveSession,
    CreateInteractiveSessionArguments,
    QCrBoxErrorResponse,
)
from qcrboxapiclient.types import File

from django.conf import settings
from . import models

logger = logging.getLogger(__name__)

# Set the string length above which non-error API responses will be truncated in the logs
max_length_api_log = 10000

# Utility class for returning API responses / errors

class response(object):
    def __init__(self, payload=None):
        self.body = payload

        if isinstance(self.body, QCrBoxErrorResponse):
            # If the upload fails, give response an error flag, log it
            logger.error(f'Error response from API: {self.body}')
            self.is_valid = False

        else:
            # Truncate the API response to sent to the logger if its a success
            logtext = str(self.body)
            if len(logtext)>max_length_api_log:
                logtext=logtext[:max_length_api_log-2]+' ... '+logtext[-2:]
            logger.info(f'Response from API: {logtext}')
            self.is_valid = True


# ==========================================
# ========= API functionality here =========
# ==========================================

# Quick-reference function to create new client
def get_client():
    client = Client(base_url=settings.API_BASE_URL)
    return client


# ----- Basic API I/O Functionality -----

# Take a django InMemoryFile, prepare it, then send to the API to upload to the backend
def upload_dataset(im_file):
    client = get_client()
    file_bytes = im_file.file
    file_name = str(im_file)

    payload_file = File(file_bytes, file_name)
    upload_payload = CreateDatasetBody(payload_file)

    logger.info(f'API call: create_dataset')
    raw_response = create_dataset.sync(client=client, body=upload_payload)
    
    return response(raw_response)

# Fetch a datafile from the backend and serve to the user
def download_dataset(dataset_id):
    client = get_client()

    logger.info(f'API call: download_dataset_by_id, id={dataset_id}')
    raw_response = download_dataset_by_id.sync(client=client, id=dataset_id)

    return response(raw_response)

# Instruct the backend to delete a file with a given id
def delete_dataset(dataset_id):
    client = get_client()

    logger.info(f'API call: delete_dataset_by_id, id={dataset_id}')
    raw_response = delete_dataset_by_id.sync(id=dataset_id, client=client)

    return response(raw_response)

# Fetch a dataset's backend metadata
def get_dataset(dataset_id):
    client = get_client()

    logger.info(f'API call: get_dataset_by_id, id={dataset_id}')
    raw_response = get_dataset_by_id.sync(client=client, id=dataset_id)

    return response(raw_response)


# ----- Session Functionality -----

def start_session(app_id, dataset_id):
    client = get_client()

    # Get relevant metadata instances from local db
    app = models.Application.objects.get(pk=app_id)
    dataset_metadata = models.FileMetaData.objects.get(backend_uuid=dataset_id)

    # Sessions are started with a data_file_id (not a dataset_id), so need to fetch that ID from a dataset
    get_response = get_dataset(dataset_id)

    # Check a dataset was actually found
    if not get_response.is_valid:
        return get_response

    # Get the associated data_file's ID
    datafile_id = get_response.body.payload.datasets[0].data_files[dataset_metadata.filename].qcrbox_file_id

    # Set up arguments
    arguments = CreateInteractiveSessionArguments.from_dict({"input_file": {"data_file_id": datafile_id}})
    create_session = CreateInteractiveSession(app.slug, app.version, arguments)

    # Initialise session
    logger.info(f'API call: create_interactive_session_with_arguments')
    raw_response = create_interactive_session_with_arguments.sync(client=client, body=create_session)

    return response(raw_response)

def get_session(session_id):
    client = get_client()

    logger.info(f'API call: get_interactive_session_by_id, id={session_id}')
    raw_response = get_interactive_session_by_id.sync(client=client, id=session_id)

    return response(raw_response)

def close_session(session_id):
    client = get_client()

    logger.info(f'API call: close_interactive_session, id={session_id}')
    raw_response = close_interactive_session.sync(client=client, id=session_id)

    return response(raw_response)


# ----- Fetching Application Metadata -----

def get_applications():
    client = get_client()

    logger.info(f'API call: list_applications')
    raw_response = list_applications.sync(client=client)

    return response(raw_response)