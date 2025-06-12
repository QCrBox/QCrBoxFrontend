from json import JSONDecodeError

from qcrboxapiclient.api.datasets import create_dataset, delete_dataset_by_id, download_dataset_by_id
from qcrboxapiclient.api.interactive_sessions import (
    close_interactive_session,
    create_interactive_session_with_arguments,
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

# Utility class for returning API responses / errors

class response(object):
    def __init__(self, is_valid, payload=None):
        self.is_valid = is_valid
        self.payload = payload


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
    
    if isinstance(raw_response, QCrBoxErrorResponse):
        # If the upload fails, return response with an error flag and error info
        return response(False, raw_response)

    dataset_id = raw_response.payload.datasets[0].qcrbox_dataset_id
    # Return the ID assigned to the file by the backend
    return response(True, dataset_id)

def download_dataset(file_id):
    client = get_client()

    raw_response = download_dataset_by_id.sync(client=client, id=file_id)
    
    if isinstance(raw_response, QCrBoxErrorResponse):
        # If the upload fails, return response with an error flag and error info
        return response(False, raw_response)

    return response(True, raw_response)