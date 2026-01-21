'''QCrBox Utility

Miscellaneous utility functions and classes as required by various parts of
the QCrBox Django Frontend.

'''

import re
import textwrap

from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from qcrbox import api
from qcrbox import models

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

    local_apps = models.Application.objects.all()                       # pylint: disable=no-member

    # Fetch slugs to represent apps known to the frontend
    local_appdict = {(app.name, app.version) : app for app in local_apps}
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

            # Handle change of ports, unlikely to ever happen in deployment
            elif current_app.port != app.gui_port:
                current_app.port = app.gui_port
                current_app.save()

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

        # Add commands to the new app

        for command in app.commands:

            # Ignore protected commands
            if command.name[:2] == '__':
                continue

            new_command = models.AppCommand(
                name=command.name,
                app=new_app,
                description=command.description,
                interactive=command.name=='interactive_session',
            )

            new_command.save()

            # Add information on the parameters to attach to the new command
            for param_key in command.parameters.additional_properties:
                parameter = command.parameters[param_key]

                if parameter['default_value']:
                    default_value = parameter['default_value']
                else:
                    default_value = None

                new_param = models.CommandParameter(
                    command = new_command,
                    name = param_key,
                    dtype = parameter['dtype'],
                    description = parameter['description'],
                    required = parameter['required'],
                    default = default_value
                )

                # Add any validation to the new parameter object as needed
                validation = parameter['valid_value']

                if validation:

                    # Get the highest priority validation type and save it
                    for validation_type in ('choices', 'numeric_range', 'regex'):
                        if validation_type in validation and validation[validation_type]:
                            new_param.validation_type = validation_type
                            new_param.validation_value = validation[validation_type]
                            break

                new_param.save()

        response['new_apps'].append(new_app.pk)

    # Flag local DB entries inactive if no longer present in the backend

    for app in models.Application.objects.filter(active=True):          # pylint: disable=no-member

        if (app.name, app.version) in backend_appset:
            continue

        app.active = False
        app.save()

        response['deactivated_apps'].append(app.pk)

    return response


def sanitize_command_name(command):
    '''Simple function to parse a command name for display in the dropdown
    command menu in the workflow.

    '''

    command_name = command.name.replace('_',' ').title()
    return command.app.name + ' : ' + command_name

def twrap(text, width, min_width=5, max_lines=4):
    '''Simple function to split text over a given length and reconcatenate
    the pieces with plotly-recognised <br> tokens to generate newlines.
    Returns none if the returned text would be too narrow or be over too
    many lines

    Parameters:
    - text(str): the text to be wrapped.
    - width(int): the number of characters per line of the wrapped text
    - min_width(int, optional): if the value provided for width is lower than
            this, return an empty string instead, to prevent overly narrow
            wrapped text.
    - max_lines(int, optional): if the resultant wrapped text has more than
            this many lines, return an empty string instead to prevent overly
            long wrapped text.

    '''

    if width < min_width:
        return ''
    text_split = textwrap.wrap(text, width)
    if len(text_split) > max_lines:
        return ''
    return '<br>'.join(text_split)

def paginate_objects(object_list, page, per_page=13):
    '''Paginate a list of objects (e.g. db records) using the django in-built
    paginator, with in-built error correction for e.g. empty lists or accessing
    pages out of range.

    '''

    paginator = Paginator(object_list, per_page)

    try:
        objects = paginator.get_page(page)
    except PageNotAnInteger:
        objects = paginator.page(1)
    except EmptyPage:
        objects = paginator.page(paginator.num_pages)

    return objects

def check_user_view_file_permission(user, load_file):
    ''' Check whether a given user has the permission to view a given file,
    and raise a PermissionDemied error if not'''

    file_group = load_file.group
    user_groups = user.groups.all()

    shared_groups = file_group in user_groups

    if shared_groups or user.has_perm('qcrbox.global_access'):
        pass

    else:
        raise PermissionDenied

def get_next_valid_filename(filename):
    ''' Check whether a proposed output filename already exists on record and,
    if so, modify it to prevent a clash.'''

    file_metas = models.FileMetaData.objects                            # pylint: disable=no-member
    inv_filenames = file_metas.values_list('filename', flat=True)
    if not filename in inv_filenames:
        return filename

    fname_components = filename.split('.')
    fn_root = fname_components[0]
    fn_ext = fname_components[-1]

    fn_root = re.sub(r'\(\d+\)$', '', fn_root)
    if not f'{fn_root}.{fn_ext}' in inv_filenames:
        return f'{fn_root}.{fn_ext}'

    f_ind = 1

    # Find the next valid pattern 'filename_root(x).ext' which is not already in use
    while True:
        if not f'{fn_root}({f_ind}).{fn_ext}' in inv_filenames:
            return f'{fn_root}({f_ind}).{fn_ext}'
        f_ind += 1
