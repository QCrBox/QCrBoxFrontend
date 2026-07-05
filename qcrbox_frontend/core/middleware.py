'''Custom middleware for the QCrBox frontend.'''

from django.contrib.auth.middleware import PersistentRemoteUserMiddleware

from qcrbox.request_context import reset_current_username, set_current_username


class CurrentUserMiddleware:
    '''Store the acting user's username in a request-scoped contextvar.

    This makes the username available to code that has no access to the
    request object (in particular api.get_client(), which forwards it to the
    QCrBox registry API via the X-QCrBox-User header). Must be placed after
    AuthenticationMiddleware (and after AutheliaRemoteUserMiddleware when SSO
    is enabled) so that request.user is resolved.
    '''

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        username = user.username if (user is not None and user.is_authenticated) else None
        token = set_current_username(username)
        try:
            return self.get_response(request)
        finally:
            reset_current_username(token)


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
