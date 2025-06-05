from django import template
from django.conf import settings
from django.contrib.auth.models import User, Group, Permission

register = template.Library()

# Special tag to create values for tables generated at run-time:

# When a value object is passed to a table view template with the flag is_special
# set to true, instead of fetching any values directly from the dataset, the
# appropriate line of this tag is run instead

@register.filter(name='getspecial')
def getspecial(value, arg):

    # Special user value:

    # Fetch list of names of groups associated with a user
    if arg=='groups':
        grouplist = []

        for i in value.groups.all():
            grouplist.append(str(i))

        grouplist.sort()

        return ', '.join(grouplist)


    # Special group values:

    # Fetching the number of users associated with a given group
    elif arg=='membership':
        group_id=value.pk
        return Group.objects.get(pk=group_id).user_set.all().count()

    elif arg=='owners':
        perm = Permission.objects.get(codename='edit_users')
        owners = value.user_set.filter(user_permissions=perm)

        ownerlist = []

        for owner in owners:
            ownerlist.append(str(owner))

        ownerlist.sort()

        return ', '.join(ownerlist)

    else:
        raise NotImplementedError