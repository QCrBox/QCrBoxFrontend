'''QCrBox User Views

Module containing the view methods which generate and serve http responses to
the browser when their related url is accessed.

Contains views pertaining to Logging In / Out and a read-only user list.
Users and groups themselves are managed in lldap (the single source of truth
for identities; see core.auth_backends), not in the frontend.

'''

import logging

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required

from qcrbox import forms
from qcrbox.utility import DisplayField, paginate_objects

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

    # Under Authelia SSO the Django session would be re-established from the
    # Remote-User header immediately, so the Authelia session must be ended too.
    if settings.AUTHELIA_LOGOUT_URL:
        return redirect(settings.AUTHELIA_LOGOUT_URL)

    messages.success(request, 'Logout Successful!')

    return redirect('login')

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
    })

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

    # With SSO, account details (name, email, password) live in lldap and are
    # managed via the Authelia/lldap UIs, not in the frontend mirror.
    if settings.AUTHELIA_SSO:
        messages.info(request, 'Account details are managed by the QCrBox user directory.')
        return redirect('landing')

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

    # With SSO, passwords are managed by Authelia/lldap, not the frontend.
    if settings.AUTHELIA_SSO:
        messages.info(request, 'Passwords are managed by the QCrBox user directory.')
        return redirect('landing')

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
