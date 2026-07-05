'''Request-scoped context shared with layers that have no access to the request.

Currently holds the acting user's username, set by CurrentUserMiddleware and
consumed by api.get_client() to identify the user to the QCrBox registry API.
Code running outside the request cycle (e.g. management commands) sees None
and the registry treats such calls as anonymous.
'''

from contextvars import ContextVar

_current_username: ContextVar[str | None] = ContextVar('qcrbox_current_username', default=None)


def set_current_username(username):
    '''Set the acting user's username for the current context; returns a reset token.'''
    return _current_username.set(username or None)


def reset_current_username(token):
    '''Reset the contextvar using the token returned by set_current_username.'''
    _current_username.reset(token)


def get_current_username():
    '''Return the acting user's username, or None outside an authenticated request.'''
    return _current_username.get()
