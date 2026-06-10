'''Custom middleware for the QCrBox frontend.'''

from django.contrib.auth.middleware import PersistentRemoteUserMiddleware


class AutheliaRemoteUserMiddleware(PersistentRemoteUserMiddleware):
    '''Authenticate users from the Remote-User header set by Authelia.

    The Traefik forwardAuth middleware replaces the Remote-User header on
    every request with the username verified by Authelia, so this header can
    only be trusted when the frontend is exclusively reachable through the
    reverse proxy (it must not be published on a host port).

    Unknown usernames are auto-created as Django users by RemoteUserBackend;
    group membership / permissions are still managed within Django.
    '''

    header = 'HTTP_REMOTE_USER'
