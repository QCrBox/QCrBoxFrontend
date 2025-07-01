'''QCrBox Utility

Miscellaneous utility functions and classes as required by various parts of
the QCrBox Django Frontend.

'''

from . import api
from . import models

class DisplayField():
    '''A class to contain information on fields to be displayed in 'view list'
    e.g. denoting a field which should form a column of a rendered html table
    and some metadata on how it should be rendered.

    '''

    def __init__(self, name, attr, is_header=False, is_special=False):
        '''Initialise an instance of DisplayField

        Parameters:
        - name(str): The human readable name of the field
        - attr(str): The name of the related Model attribute.  This can also
                be a recursive attribute, separated by '__': e.g., setting
                attr to 'dataset__filename' will return the 'filename'
                attribute of the DataSet object referred to in this Models's
                'dataset' attribute.
        - is_header(bool): Whether the column containing this field should be
                styled as a header column
        - is_special(bool): Whether there are any special instructions for
                generating entries in this field.  These are parsed by the
                get_special method in templatetags/getspecial.py

        Returns:
        None

        '''

        self.name = name
        self.attr = attr
        self.is_header = is_header
        self.is_special = is_special


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
    local_appdict = {(app.name, app.version) : app for app in models.Application.objects.filter()}
    local_appset = set(local_appdict.keys())

    api_response = api.get_applications()

    # If something went wrong return a flag only
    if not api_response.is_valid:
        return None

    response = {
        'new_apps' : [],
        'deactivated_apps' : [],
        'reactivated_apps' : [],
    }

    backend_appset = set([])

    # Create local DB entries for any missing apps
    backend_app_list = api_response.body.payload.applications
    for app in backend_app_list:

        backend_appset = backend_appset | set([(app.name, app.version),])

        # If frontend already knows about the app, reactivate or skip
        if (app.name, app.version) in local_appset:

            # Handle reactivating an app which was temporarily unavailable
            current_app = local_appdict[(app.name, app.version)]
            if not current_app.active:
                current_app.active = True
                current_app.save()

                response['reactivated_apps'].append(current_app.pk)

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

    # Flag local DB entries inactive if no longer present in the backend

    for app in models.Application.objects.filter(active=True):

        if (app.name, app.version) in backend_appset:
            continue

        app.active = False
        app.save()

        response['deactivated_apps'].append(app.pk)

    return response
