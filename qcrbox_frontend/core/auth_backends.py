'''Authentication backends for the QCrBox frontend.

With Authelia SSO enabled, lldap is the single source of truth for users and
group membership: Django's user/group records are a read-only mirror synced
from the Remote-Groups header on login, and role permissions are attached to
reserved lldap groups instead of individual users.
'''

import logging

from django.contrib.auth.backends import RemoteUserBackend
from django.contrib.auth.models import Group, Permission

LOGGER = logging.getLogger(__name__)

# Reserved lldap groups that carry QCrBox roles. Membership of one of these
# groups grants the mapped permissions (via Django's group permissions);
# everything else about a user's abilities derives from plain group
# membership. Create these groups in the lldap UI (https://users.<domain>).
ROLE_GROUP_PERMISSIONS = {
    'qcrbox_global_managers': ['edit_users', 'edit_data', 'global_access'],
    'qcrbox_group_managers': ['edit_users', 'edit_data'],
    'qcrbox_data_managers': ['edit_data'],
}

# lldap's internal groups (e.g. lldap_admin, lldap_password_manager) are used
# by Authelia's access rules and must not be mirrored as data-sharing groups.
EXCLUDED_GROUP_PREFIXES = ('lldap_',)


def sync_user_groups(user, remote_groups_header):
    '''Mirror a user's Django group memberships from the Remote-Groups header.

    Groups are created on first sight and never deleted (dataset ACLs
    reference them); only the user's memberships are replaced. Reserved role
    groups get their permissions (re-)attached idempotently.

    Parameters:
    - user(User): the authenticated Django user to sync.
    - remote_groups_header(str): comma-separated group list from Authelia.

    '''

    group_names = [name.strip() for name in (remote_groups_header or '').split(',') if name.strip()]
    mirrored_names = [name for name in group_names if not name.startswith(EXCLUDED_GROUP_PREFIXES)]

    groups = []
    for name in mirrored_names:
        group, _created = Group.objects.get_or_create(name=name)
        if name in ROLE_GROUP_PERMISSIONS:
            _ensure_role_permissions(group, ROLE_GROUP_PERMISSIONS[name])
        groups.append(group)

    user.groups.set(groups)
    LOGGER.info(
        'Synced groups for user %s from Authelia: %s',
        user.username,
        ', '.join(mirrored_names) or '(none)',
    )


def _ensure_role_permissions(group, permission_codenames):
    '''Attach the role's permissions to the mirrored group (idempotent).'''

    permissions = Permission.objects.filter(codename__in=permission_codenames)
    group.permissions.set(permissions)


class AutheliaRemoteUserBackend(RemoteUserBackend):
    '''RemoteUserBackend that also mirrors group membership from Authelia.

    Group sync happens whenever the backend authenticates the Remote-User
    header. Note that PersistentRemoteUserMiddleware only re-authenticates at
    the start of a browser session, so membership changes in lldap take
    effect on the user's next login.
    '''

    def authenticate(self, request, remote_user):
        user = super().authenticate(request, remote_user)
        if user is not None and request is not None:
            sync_user_groups(user, request.META.get('HTTP_REMOTE_GROUPS', ''))
        return user
