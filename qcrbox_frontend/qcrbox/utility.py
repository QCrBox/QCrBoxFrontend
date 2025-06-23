import logging

from . import api
from . import models

logger = logging.getLogger(__name__)

# Update applications list by syncing with the results of an API polling
def update_applications():

    # Fetch slugs to represent apps known to the frontend
    local_appset = {(app.name, app.version) for app in models.Application.objects.all()}

    api_response = api.get_applications()

    # If something went wrong return a flag only
    if not api_response.is_valid:
        return None

    response = {
        'new_apps' : [],
        'deactivated_apps' : [],
    }

    backend_appset = set([])

    # Create local DB entries for any missing apps
    backend_app_list = api_response.body.payload.applications
    for app in backend_app_list:

        backend_appset = backend_appset | set([(app.name, app.version),])

        # If frontend already knows about the app, do nothing
        if (app.name, app.version) in local_appset:
            continue

        if not app.gui_port:
            logger.warning(f'No GUI port found for app {app.name} version {app.version}: skipping!')
            continue

        new_app = models.Application(
            name=app.name,
            slug=app.slug,
            url=app.url,
            version=app.version,
            description=app.description,
            port=app.gui_port,
            active=True,
        )
        new_app.save()

        response['new_apps'].append(new_app.pk)

    # Flag local DB entried inactive if no longer present in the backend

    for app in models.Application.objects.filter(active=True):

        if (app.name, app.version) in backend_appset:
            continue

        app.active=False
        app.save()

        response['deactivated_apps'].append(app.pk)

    return response

