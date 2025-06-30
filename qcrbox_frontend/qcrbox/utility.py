'''QCrBox Utility

Miscellaneous utility functions as required by various parts of the QCrBox
Django Frontend.

'''

from . import api
from . import models

def update_applications():
    '''Obtain a list of installed QCrBox Applications from the API, and update
    the Frontend Applications database accordingly.  Applications present in
    the API-returned list but not present in the Frontend db are added to the
    Frontend db (along with config info such as port number), whereas
    applicarions present in the Frontend db but not in the API-returned list
    are edited to be flagged as inactive in the Frontend db.  Applications are
    uniquely identified by a tuple of the form (name, version).

    Parameters:
    None

    Returns:
    - response(dict): a dictionary containing two lists:
    -- response['new_apps'](list): lists the Frontend db primary keys of all
            applications added by this method.
    -- response['deactivated_apps'](list): lists the Frontend db primary
            keys of all applications deactivated by this method.

    '''

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

        app.active = False
        app.save()

        response['deactivated_apps'].append(app.pk)

    return response
