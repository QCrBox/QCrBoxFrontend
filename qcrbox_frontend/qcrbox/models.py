from django.db import models
from django.contrib.auth.models import User, Group

# Metadata on available files
class FileMetaData(models.Model):
    filename = models.CharField(max_length=255)
    backend_uuid = models.CharField(max_length=255, null=True)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    filetype = models.CharField(max_length=255, null=True)

# Metadata on available applications for interactive sessions
class Application(models.Model):
    name = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    version = models.CharField(max_length=255)

# Metadata on a session; what file was given as input, which application was used, what file was output
class ProcessStep(models.Model):
    application = models.ForeignKey(Application, null=True, on_delete=models.SET_NULL)
    infile = models.ForeignKey(FileMetaData, null=True, on_delete=models.SET_NULL, related_name='processed_to')
    outfile = models.ForeignKey(FileMetaData, null=True, on_delete=models.SET_NULL, related_name='processed_by')

# Create an empty model to assign global permissions to to be independent of models
class DataPermissionSupport(models.Model):
    class Meta:
        
        managed = False  # No database table creation or deletion operations will be performed for this model. 
                
        default_permissions = () 
        permissions = ( 
            ('edit_users', 'Can add, edit, delete other users, by default just within their groups.'),
            ('global_access', 'Can CRUD everything outside of their group(s).')
        )
