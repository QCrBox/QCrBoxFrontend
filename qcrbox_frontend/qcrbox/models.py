'''QCrBox Models

The collection of Model classes which determine the structure of the Frontend
database and provide the endpoints from which to run queries.

'''

from django.db import models
from django.contrib.auth.models import User, Group

class FileMetaData(models.Model):
    '''The FileMetaData model stores information on Datasets; the actual files
    that make up a Dataset are handled exclusively in the backend and are only
    touched by the frontend when uploading a new file or downloading a file
    from the backend via the frontend.

    The FileMetaData model allows the frontend to keep track of Datasets
    vicariously, including information on their history, ownership, date
    of creation and the ID by which they are stored on the backend.

    Contains the following attributes:
    - filename(str): the name of the filename, matching the name of the
            Datafile within the Dataset created in the backend upon uploading
            a new file from the frontend
    - display_filename(str): the filename to be displayed by the frontend.
            Generally the same as filename, but with a bracketed number (e.g.
            (2) ) appended to the end of it in cases where files would
            otherwise have the same name.  Helps to prevent user ambiguity.
    - backend_uuid(str): the ID string pointing to where the Dataset is stored
            on the backend
    - user(User): the User object of the user that uploaded this file or
            created it as output from an Interactive Session.
    - group(Group): the Group object of the group to which this file is
            associated.
    - filetype(str): the filetype (e.g. extension) of the file
    - creation_time(datetime): the date/time the file was created
    - active(bool): a flag to indicate whether the file is 'active'.  This
            is set to False when the corresponding Dataset has been deleted
            from the backend, and massively limits the functionality
            available when working with this dataset (e.g. it cannot be
            selected to start a workflow, it won't show up when viewing the
            list of files, etc).

    '''

    filename = models.CharField(max_length=255)
    display_filename = models.CharField(max_length=255)
    backend_uuid = models.CharField(max_length=255, null=True)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    filetype = models.CharField(max_length=255, null=True)
    creation_time = models.DateTimeField(auto_now_add=True)

    active = models.BooleanField(default=True)

    def __str__(self):
        '''Return the filename when an instance of this is parsed as string'''
        max_len = 30

        if len(self.display_filename) < max_len:
            return str(self.display_filename)
        return str(str(self.display_filename)[:max_len-3]+'...')


class Application(models.Model):
    '''The Application model stores information on Applications; e.g. the
    tools which have been installed as part of QCrBox (not QCrBox Frontend).

    Contains the following attributes:
    - name(str): the human-readable name of the Application
    - url(str): a url which links to an external site with more information on
            the given Application
    - version(str): the version of the Application
    - description(str): a short human-readable description of the Application
    - slug(str): the string used to uniquely refer to the Application in the
            backend.
    - port(str): the port through which an Interactive Session of this app
            can be accessed via the browser, if one exists
    - active(bool): a flag to indicate whether the application is 'active'.
            This is set to False when the corresponding Application has been
            deleted or upgraded, and massively limits the functionality
            available when working with this Application (e.g. it cannot be
            selected to start an Interactive Session).

    '''

    name = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    version = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True, max_length=1023)
    slug = models.CharField(max_length=255)

    # Specify which port is assigned to VNC sessions of the given app
    port = models.IntegerField(default=0, null=True)

    active = models.BooleanField(default=True)

    def __str__(self):
        '''Return the name when an instance of this is parsed as string'''

        return str(self.name)


class AppCommand(models.Model):
    '''The AppCommand model stores information on commands; e.g. the commands
    associated with the tools which have been installed as part of QCrBox
    (not QCrBox Frontend).

    Contains the following attributes:
    - app(Application): the Application to which this command belongs
    - name(str): the name of the command
    - description(str): the human-readable description of a command
    - interactive(bool): a boolean to denote whether this command opens an
            interactive session of the attached app.

    '''

    app = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='commands')
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=1023, null=True, blank=True)
    interactive = models.BooleanField(default=False)

    def __str__(self):
        '''Return the human-readably parsed name of the command name'''

        return str(self.name).replace('_',' ').title()


class CommandParameter(models.Model):
    '''The CommandParameter model stores information on an input parameter
    for a given AppCommand, including their name, dtype, default value, etc.
    Used to generate forms to collact parameters from the user when generating
    a command, and used when calling that command via the API.

    Contains the following attributes:
    - command(AppCommand): the command to which this parameter belongs
    - name(str): the display name of the parameter
    - dtype(str): the expected data type for the parameter, used when
            determining which form widget to display.
    - description(str): the text description of the parameter.
    - required(bool): whether user input is required.
    - default(str): the JSON-serialized default value for the parameter, if
            applicable.
    - validation_type(str): the type of validation that should be applied to
            this parameter (numeric_range, choices or regex).
    - validation_value(str): a string representing the validation which should
            be applied (e.g. a [a, b] for numeric_range, [options...] for
            choices or a regex string for regex.

    '''

    command = models.ForeignKey(AppCommand, on_delete=models.CASCADE, related_name='parameters')
    name = models.CharField(max_length=255)
    dtype = models.CharField(max_length=255)
    description = models.TextField(max_length=1023, blank=True, null=True)
    required = models.BooleanField()
    default = models.CharField(max_length=255, null=True, blank=True)
    validation_type = models.CharField(max_length=255, null=True, blank=True)
    validation_value = models.CharField(max_length=255, null=True, blank=True)


class ProcessStep(models.Model):
    '''The ProcessStep model stores information pertaining to any process
    which takes an input Dataset and generates an output Dataset, e.g. an
    Interactive Session, and is used to preserve information on the the
    creation history and ancestry of a Dataset.

    Contains the following attributes:
    - command(AppCommand): the AppCommand instance which corresponds to
            the application command used for this process.
    - infile(FileMetaData): the metadata of the Dataset provided as input.
    - outfile(FileMetaData): the metadata of the Dataset yielded as output.
    - parameters(str): a JSON-serialised dictionary of parameters and their
            values used in this process.

    '''

    command = models.ForeignKey(
        AppCommand,
        null=True,
        on_delete=models.SET_NULL
    )
    infile = models.ForeignKey(
        FileMetaData,
        null=True,
        on_delete=models.SET_NULL,
        related_name='processed_to',
    )
    outfile = models.ForeignKey(
        FileMetaData,
        null=True,
        on_delete=models.SET_NULL,
        related_name='processed_by'
    )
    parameters = models.CharField(
        max_length=255,
        default='{}',
    )


class SessionReference(models.Model):
    '''A model which stores temporary records on any currently active
    sessions.  Allows for these sessions to be accessed and closed in the
    event that a users lose the cookies referring to their active
    sessions.  Records should be deleted when the respective session is
    closed.

    Contains the following attributes:
    - user(User): the User that initiated the session (for, e.g., determining
            their permission to close it, not currently implemented).
    - command(AppCommand): the AppCommand instance which corresponds to
            the command used in this session.
    - session_id(str): the ID used to access the session in the backend.
    - start_time(datetime): the time when the session began

    '''

    user = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL
    )
    command = models.ForeignKey(
        AppCommand,
        null=True,
        on_delete=models.CASCADE
    )
    session_id = models.CharField(max_length=255)
    start_time = models.DateTimeField(auto_now_add=True)


# Create an empty model to assign global permissions to to be independent of models
class DataPermissionSupport(models.Model):
    '''A 'model' which exists for the sole purpose of allowing the creation
    of custom user permissions.  Contains no attributes or instances and is
    not linked to a database table.

    '''

    class Meta:                                            # pylint: disable=too-few-public-methods
        '''Additional model configuration'''

        managed = False  # No database table creation or deletion operations will be performed
                         # for this model.

        default_permissions = ()
        permissions = (
            (
                'edit_users',
                'Can add, edit, delete other users, by default just within their groups.'
            ),
            (
                'edit_data',
                'Can edit/delete the metadata for uploaded/created files.'
            ),
            (
                'global_access',
                'Can CRUD things outside of their group(s).'
            ),
        )
