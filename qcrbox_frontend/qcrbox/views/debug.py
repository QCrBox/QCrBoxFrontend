'''QCrBox Debug

Module containing the view methods which generate and serve http responses to
the browser when their related url is accessed.

Contains views pertaining to Debugging and admin panels.

'''

import logging
import os

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.static import serve

from qcrbox.plotly_dash import plotly_app                           # pylint: disable=unused-import

LOGGER = logging.getLogger(__name__)


@login_required(login_url='login')
def frontend_logs(request):
    '''A view to fetch the frontend logs and return them as a download.
    Strictly for debugging purposes only, and only permitted to superusers.

    '''

    if not request.user.is_superuser:
        raise PermissionDenied
    filepath = 'qcrbox.log'
    return serve(request, os.path.basename(filepath), os.path.dirname(filepath))
