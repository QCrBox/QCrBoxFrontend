'''Special tag to create values for tables generated at run-time:

When a value object is passed to a table view template with the flag is_special
set to true, instead of fetching any values directly from the dataset, the
appropriate line of this tag is run instead and the output value is returned.

'''

from django import template
from django.contrib.auth.models import Group, Permission

REGISTER = template.Library()

@REGISTER.filter(name='getspecial')
def getspecial(value, arg):
    '''Template tag configuration'''

    # Special user value:

    # Fetch list of names of groups associated with a user
    if arg == 'groups':
        grouplist = []

        for i in value.groups.all():
            grouplist.append(str(i))

        grouplist.sort()

        return ', '.join(grouplist)

    # Convert a user's permissions set into a human-readable list
    if arg == 'role':
        roles = []

        for (perm, name) in [
                ('global_access', 'Admin'),
                ('edit_data', 'Data Manager'),
                ('edit_users', 'Group Manager'),
        ]:
            if value.has_perm('qcrbox.' + perm):
                roles.append(name)

        if len(roles) == 0:
            return 'User'
        return ', '.join(roles)


    # Special group values:

    # Fetching the number of users associated with a given group
    if arg == 'membership':
        group_id = value.pk
        return Group.objects.get(pk=group_id).user_set.all().count()

    if arg == 'owners':
        perm = Permission.objects.get(codename='edit_users')
        owners = value.user_set.filter(user_permissions=perm)

        ownerlist = []

        for owner in owners:
            ownerlist.append(str(owner))

        ownerlist.sort()

        return ', '.join(ownerlist)


    # Special metadata values:
    if arg == 'created_from':
        if value.processed_by.all():
            process = value.processed_by.first()
            if process.infile:
                if process.infile.active:
                    return process.infile
                return '[File Deleted]'
        return '-'

    if arg == 'created_app':
        if value.processed_by.all():
            process = value.processed_by.first()
            if process.application:
                return process.application
        return '-'

    # If arg doesn't match any option, raise exception
    raise NotImplementedError
