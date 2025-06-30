"""QCrBox Models

The collection of Model classes which determine the structure of the Frontend
database and provide the endpoints from which to run queries.

"""

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

        return self.filename


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
            can be accessed via the browser
    - active(bool): a flag to indicate whether the application is 'active'.
            This is set to False when the corresponding Application has been
            deleted or upgraded, and massively limits the functionality
            available when working with this Application (e.g. it cannot be
            selected to start an Interactive Session).

    '''

    name = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    version = models.CharField(max_length=255)
    description = models.CharField(blank=True, null=True, max_length=255)
    slug = models.CharField(max_length=255)

    # Specify which port is assigned to VNC sessions of the given app
    port = models.IntegerField(default=0)

    active = models.BooleanField(default=True)

    def __str__(self):
        '''Return the name when an instance of this is parsed as string'''

        return self.name

# Metadata on a session; what file was given as input, which application was used, what file was output
class ProcessStep(models.Model):
    '''The ProcessStep model stores information pertaining to any process
    which takes an input Dataset and generates an output Dataset, e.g. an
    Interactive Session, and is used to preserve information on the the
    creation history and ancestry of a Dataset.

    Contains the following attributes:
    - application(Application): the Application instance which corresponds to
            the application used for this process.
    - infile(FileMetaData): the metadata of the Dataset provided as input.
    - outfile(FileMetaData): the metadata of the Dataset yielded as output.

    '''

    application = models.ForeignKey(
        Application,
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

# Create an empty model to assign global permissions to to be independent of models
class DataPermissionSupport(models.Model):
    '''A 'model' which exists for the sole purpose of allowing the creation
    of custom user permissions.  Contains no attributes or instances and is
    not linked to a database table.

    '''

    class Meta:
        '''Additional model configuration'''

        managed = False  # No database table creation or deletion operations will be performed for this model.

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
