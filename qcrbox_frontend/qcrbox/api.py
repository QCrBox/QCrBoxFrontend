from qcrboxapiclient.api.datasets import (
    create_dataset,
    delete_dataset_by_id,
    download_dataset_by_id,
    get_dataset_by_id
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

# Utility class for returning API responses / errors

class response(object):
    def __init__(self, payload=None):
        self.body = payload

        if isinstance(self.body, QCrBoxErrorResponse):
            # If the upload fails, give response an error flag
            self.is_valid = False

        else:
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

    raw_response = create_dataset.sync(client=client, body=upload_payload)
    
    return response(raw_response)

# Fetch a datafile from the backend and serve to the user
def download_dataset(dataset_id):
    client = get_client()

    raw_response = download_dataset_by_id.sync(client=client, id=dataset_id)

    return response(raw_response)

# Instruct the backend to delete a file with a given id
def delete_dataset(dataset_id):
    client = get_client()

    raw_response = delete_dataset_by_id.sync(id=dataset_id, client=client)

    return response(raw_response)


# ----- Session Functionality -----

def start_session(app_id, dataset_id):
    client = get_client()

    # Get relevant metadata instances from local db
    app = models.Application.objects.get(pk=app_id)
    dataset_metadata = models.FileMetaData.objects.get(backend_uuid=dataset_id)

    # Sessions are started with a data_file_id (not a dataset_id), so need to fetch that ID from a dataset
    raw_get_response = get_dataset_by_id.sync(client=client, id=dataset_id)

    # Check a dataset was actually found
    if isinstance(raw_get_response, QCrBoxErrorResponse):
        return response(raw_get_response)

    # Get the associated data_file's ID
    datafile_id = raw_get_response.payload.datasets[0].data_files[dataset_metadata.filename].qcrbox_file_id

    # Set up arguments
    arguments = CreateInteractiveSessionArguments.from_dict({"input_file": {"data_file_id": datafile_id}})
    create_session = CreateInteractiveSession(app.name, app.version, arguments)

    # Initialise session
    raw_response = create_interactive_session_with_arguments.sync(client=client, body=create_session)

    return response(raw_response)

def get_session(session_id):
    client = get_client()

    raw_response = get_interactive_session_by_id.sync(client=client, id=session_id)

    return response(raw_response)