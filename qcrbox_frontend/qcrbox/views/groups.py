'''QCrBox Group Views

Module containing the view methods which generate and serve http responses to
the browser when their related url is accessed.

Contains views pertaining to Group creation / management.

'''

import logging

from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import PermissionDenied

from qcrbox import forms
from qcrbox.utility import DisplayField, paginate_objects
from qcrbox.views import generic

LOGGER = logging.getLogger(__name__)


# Can only edit groups if user has the global access perm
@permission_required('qcrbox.global_access')
def create_group(request):
    '''A view to handle rendering the 'create new group' page and handle the
    creation of a new group on the submittal of the embedded form.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    if request.method == 'POST':

        # Get the posted form
        form = forms.GroupForm(request.POST)

        if form.is_valid():
            name = form.data['name']
            form.save()
            LOGGER.info(
                'User %s created new group "%s"',
                request.user.username,
                name,
            )
            messages.success(request, (f'New Group "{name}" added!'))
    else:
        form = forms.GroupForm()

    return render(request, 'create_generic.html', {
        'form':form,
        'instance_name':'Group',
    })

@login_required(login_url='login')
def view_groups(request):
    '''A view to handle generating and rendering the 'view group list' page.
    The contents of this page are filtered based on the request user's
    permissions and are paginated.

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
        'edit_perms':request.user.has_perm('qcrbox.global_access'),
        'edit_link':'edit_group',
        'delete_link':'delete_group',
        'create_link':'create_group',
    })

@permission_required('qcrbox.global_access', raise_exception=True)
def update_group(request, group_id):
    '''A view to handle rendering the 'edit group' page and handle the
    updating of a group on the submittal of the embedded form.  Based on
    generic.update().

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - group_id(int): the Frontend db primary key of the group being
            edited.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    # User should have both global access AND edit permissions to be able to do this
    if not request.user.has_perm('qcrbox.edit_users'):
        raise PermissionDenied

    return generic.update(
        request=request,
        model=Group,
        obj_id=group_id,
        meta={
            'obj_type':'Group',
            'model_form':forms.GroupForm,
            'link_suffix':'groups',
        },
        user_is_affiliated=True
    )

@permission_required('qcrbox.global_access', raise_exception=True)
def delete_group(request, group_id):
    '''A view to handle the deletion of groups.  Based on generic.delete().

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - group_id(int): the Frontend db primary key of the group being
            deleted.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    # User should have both global access AND edit permissions to be able to do this
    if not request.user.has_perm('qcrbox.edit_users'):
        raise PermissionDenied

    return generic.delete(
        request=request,
        model=Group,
        obj_id=group_id,
        meta={
            'obj_type':'Group',
            'link_suffix':'groups',
        },
        user_is_affiliated=True,
    )
