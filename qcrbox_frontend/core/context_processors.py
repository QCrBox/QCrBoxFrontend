'''Template context processors for the QCrBox frontend.'''

from django.conf import settings


def qcrbox_auth(request):
    '''Expose SSO-related settings so templates can adapt to the auth mode.'''

    return {
        'authelia_sso': settings.AUTHELIA_SSO,
        'lldap_admin_url': settings.LLDAP_ADMIN_URL,
    }
