'''QCrBox User Views

Module containing the view methods which generate and serve http responses to
the browser when their related url is accessed.

Contains views pertaining to User creation / management and Logging In / Out.

'''

import logging

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User, Permission
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import permission_required, login_required

from qcrbox import forms
from qcrbox.utility import DisplayField, paginate_objects
from qcrbox.views import generic

LOGGER = logging.getLogger(__name__)


def login_view(request):
    '''A view to handle rendering the login page and logging in users.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            LOGGER.info(
                'User %s logged in',
                username,
            )
            messages.success(request, 'Login Successful: Welcome, '+str(request.user))
            return redirect('landing')

        LOGGER.info(
            'User %s failed to log in',
            username,
        )
        messages.warning(request, 'Login Failed, try again!')

    return render(request, 'login.html', {})

@login_required(login_url='login')
def logout_view(request):
    '''A view to handle logging out a user.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    username = request.user.username
    logout(request)
    LOGGER.info(
        'User %s logged out',
        username,
    )
    messages.success(request, 'Logout Successful!')

    return redirect('login')

@permission_required('qcrbox.edit_users', raise_exception=True)
def create_user(request):
    '''A view to handle rendering the 'create new user' page and handle the
    creation of a new user on the submittal of the embedded form.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    if request.method == 'POST':

        form = forms.RegisterUserForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']

            # Collect pk of desired user type from form checkboxes
            user_groups = form.cleaned_data['user_groups']

            # Fetch the user we just created
            new_user = User.objects.get(username=username)

            # Populate the user info
            new_user.first_name = form.cleaned_data['first_name']
            new_user.last_name = form.cleaned_data['last_name']
            new_user.email = form.cleaned_data['email']
            new_user.save()

            # Add user to the selected user group
            for user_group in user_groups.all():

                user_group.user_set.add(new_user)

            # Add non-group related permissions
            if form.cleaned_data['group_manager']:
                new_user.user_permissions.add(Permission.objects.get(codename='edit_users'))

            if form.cleaned_data['data_manager']:
                new_user.user_permissions.add(Permission.objects.get(codename='edit_data'))

            if form.cleaned_data['global_access']:
                new_user.user_permissions.add(Permission.objects.get(codename='global_access'))

            LOGGER.info(
                'User %s created new user "%s"',
                request.user.username,
                new_user.username,
            )
            messages.success(request, 'Registration Successful!')
            form = forms.RegisterUserForm(user=request.user)
    else:
        form = forms.RegisterUserForm(user=request.user)

    return render(request, 'create_generic.html', {
        'form':form,
        'instance_name':'User',
    })

@login_required(login_url='login')
def view_users(request):
    '''A view to handle generating and rendering the 'view user list' page.
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
        DisplayField('Username', 'username', is_header=True),
        DisplayField('First Name', 'first_name'),
        DisplayField('Last Name', 'last_name'),
        DisplayField('Email', 'email'),
        DisplayField('Group(s)', 'groups', is_special=True),
        DisplayField('Role', 'role', is_special=True),
        ]

    # If a user can view unaffiliated data, they can view it all
    if request.user.has_perm('qcrbox.global_access'):
        object_list = User.objects.all()
    else:
        object_list = User.objects.filter(groups__in=request.user.groups.all())

    object_list = object_list.order_by('username')
    page = request.GET.get('page')

    objects = paginate_objects(object_list, page)

    return render(request, 'view_list_generic.html', {
        'objects': objects,
        'type':'User',
        'fields':fields,
        'edit_perms':request.user.has_perm('qcrbox.edit_users'),
        'edit_link':'edit_user',
        'delete_link':'delete_user',
        'create_link':'create_user',
    })

@permission_required('qcrbox.edit_users', raise_exception=True)
def update_user(request, user_id):
    '''A view to handle rendering the admin-level 'edit user' page and
    handle the updating of a user on the submittal of the embedded form.
    Based on generic.update().

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - user_id(int): the Frontend db primary key of the user being
            edited.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    edit_user_groups = User.objects.get(pk=user_id).groups.all()
    current_user_groups = request.user.groups.all()

    shared_groups = edit_user_groups & current_user_groups

    return generic.update(
        request=request,
        model=User,
        obj_id=user_id,
        meta={
            'obj_type':'User',
            'model_form':forms.UpdateUserForm,
            'link_suffix':'users',
        },
        user_is_affiliated=shared_groups.exists(),
    )

@login_required(login_url='login')
def edit_user(request):
    '''A view to handle the user-level 'edit user' page; i.e., the form any
    user can use to modify their own account settings.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    form = forms.EditUserForm(request.POST or None, instance=request.user)

    if request.method == 'POST':
        if form.is_valid():
            form.save()

            LOGGER.info(
                'User %s updated their account',
                request.user.username,
            )
            messages.success(request, 'Account updated successfully!')

            return redirect('landing')

    return render(request, 'update_generic.html', {
        'type':'User',
        'object':request.user,
        'form':form,
        'view_link':'landing',
    })

@login_required(login_url='login')
def update_password(request):
    '''A view to handle the user-level 'change password' page; i.e., the form
    any user can use to modify their own account password.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)

            LOGGER.info(
                'User %s changeed their password',
                request.user.username,
            )
            messages.success(request, 'Password updated successfully!')

            return redirect('landing')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'update_generic.html', {
        'type':'password for',
        'object':request.user,
        'form':form,
        'view_link':'landing',
    })

@permission_required('qcrbox.edit_users', raise_exception=True)
def delete_user(request, user_id):
    '''A view to handle the deletion of users.  Based on generic.delete().

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - user_id(int): the Frontend db primary key of the user being
            deleted.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    # Stop an admin accidentally deleting themself
    if int(request.user.pk) == int(user_id):
        messages.warning(request, 'Cannot delete current account from this view.')
        return redirect('view_users')

    deletion_user_groups = User.objects.get(pk=user_id).groups.all()
    current_user_groups = request.user.groups.all()

    shared_groups = deletion_user_groups & current_user_groups

    return generic.delete(
        request=request,
        model=User,
        obj_id=user_id,
        meta={
            'obj_type':'User',
            'link_suffix':'users',
        },
        user_is_affiliated=shared_groups.exists(),
    )
