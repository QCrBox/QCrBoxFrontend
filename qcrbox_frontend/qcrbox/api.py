from qcrboxapiclient.api.datasets import create_dataset, delete_dataset_by_id
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

# --==-- API functionality here --==--

# Quick-reference function to create new client
def get_client():
    client = Client(base_url=settings.API_BASE_URL)
    return client

def upload_dataset(file_bytes):
    client = get_client()

    payload_file = File(file_bytes)
    upload_payload = CreateDatasetBody(payload_file)

    response = create_dataset.sync(client=client, body=upload_payload)
    if isinstance(response, QCrBoxErrorResponse):
        return None

    dataset_id = response.payload.datasets[0].qcrbox_dataset_id
    return dataset_id