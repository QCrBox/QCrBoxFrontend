'''QCrBox Group Views

Module containing the view methods which generate and serve http responses to
the browser when their related url is accessed.

Groups are managed in lldap (the single source of truth for users and group
membership; see core.auth_backends); the frontend only offers a read-only
mirror of the groups relevant to the requesting user.

'''

import logging

from django.shortcuts import render
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required

from qcrbox.utility import DisplayField, paginate_objects

LOGGER = logging.getLogger(__name__)


@login_required(login_url='login')
def view_groups(request):
    '''A view to handle generating and rendering the read-only 'view group
    list' page. The contents of this page are filtered based on the request
    user's permissions and are paginated.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    fields = [
        DisplayField('Name', 'name', is_header=True),
        DisplayField('Owner(s)', 'owners', is_special=True),
        DisplayField('# Members', 'membership', is_special=True),
        ]

    # If a user can view unaffiliated data, they can view it all
    if request.user.has_perm('qcrbox.global_access'):
        object_list = Group.objects.all()
    else:
        object_list = request.user.groups.all()

    object_list = object_list.order_by('name')
    page = request.GET.get('page')

    objects = paginate_objects(object_list, page)

    return render(request, 'view_list_generic.html', {
        'objects':objects,
        'type':'Group',
        'fields':fields,
    })
