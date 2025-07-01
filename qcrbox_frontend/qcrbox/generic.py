'''Generic Views: a collection of Django View-like functions which can be used
in views.py to more Pythonically generate views when multiple similar views
with slight differences are needed, i.e. CRUD views for each editable django
Model.

'''

import logging

from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied

LOGGER = logging.getLogger(__name__)


def update(
        request,
        model,
        obj_id,
        meta,
        user_is_affiliated=False,
        **kwargs
    ):
    '''A genericised framework to generate a django response which generates
    and serves a page containing an update form for a given database model,
    and processes the submitting of that form.  This view should never be
    called directly by a user, and as such does not have an associated url;
    this method is instead called by other view methods.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - model(ModelBase): the base class for the Model which is editable on the
            page returned by this view.
    - obj_id(int): the primary key of the instance of the chosen Model which is
            the target of this edit attempt.
    - meta(dict): additional parameters required for the page to be rendered.
            should contain the following elements:
        -- meta['obj_type'](str): the human-readable name given to instances of
                the Model, e.g. 'Application', for deletion.
        -- model_form(Form): the django form for creating/editing instances of
                the chosen Model.
        -- meta['link_suffix'](str): the suffix of the URL associated with the
            'view list' view of the chosen model.  The django IDs of 'View
            list' view urls are standardised in the form 'view_[slug]', where
            the slug should be passed as this parameter.  This is used to
            generate the redirect response upon a succesful deletion.
    - user_is_affiliated(bool): an optional boolean to denote whether the
            user associated with the request is in some way affiliated with
            the instance being edited (i.e., the user belongs to the Group
            associated with a given Dataset).  If set to False, the user will
            only be given permission to edit the instance if they also have
            the 'qcrbox.global_access' permission.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    obj_type = meta['obj_type']

    # If user is flagged as able to access unaffiliated data, always continue
    if request.user.has_perm('qcrbox.global_access'):
        pass

    # Allow for an access-point check if a user is affiliated with the company to which the data
    # pertains, to prevent users editing things they shouldnt
    elif not user_is_affiliated:
        LOGGER.info(
            'User %s denied permission to modify %s (pk=%d) (unaffiliated)',
            request.user.username,
            obj_type,
            obj_id,
        )
        raise PermissionDenied()

    instance = model.objects.get(pk=obj_id)
    form = meta['model_form'](request.POST or None, instance=instance, **kwargs)

    if form.is_valid():
        form.save()

        LOGGER.info(
            'User %s updated %s "%s"',
            request.user.username,
            obj_type,
            instance,
        )
        messages.success(request, f'Changes to "{instance}" saved!')
        return redirect('view_'+meta['link_suffix'])

    return render(request, 'update_generic.html', {
        'type':obj_type,
        'object':instance,
        'form':form,
        'view_link':'view_'+meta['link_suffix'],
        })


def delete(request, model, obj_id, meta, user_is_affiliated=False):
    '''A genericised framework to generate a django response which processes
    the deletion of a given Model instance.  This view should never be called
    directly by a user, and as such does not have an associated url; this
    method is instead called by other view methods.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - model(ModelBase): the base class for the Model which is to be deleted.
    - obj_id(int): the primary key of the instance of the chosen Model which
            is the target of this delete attempt.
    - meta(dict): additional parameters required for the page to be rendered.
            should contain the following elements:
        -- meta['obj_type'](str): the human-readable name given to instances
                of the Model, e.g. 'Application', for deletion.
        -- meta['link_suffix'](str): the suffix of the URL associated with the
                'view list' view of the chosen model.  The django IDs of 'View
                list' view urls are standardised in the form 'view_[slug]',
                where the slug should be passed as this parameter.  This is
                used to generate the redirect response upon a succesful
                deletion.
    - user_is_affiliated(bool): an optional boolean to denote whether the
            user associated with the request is in some way affiliated with
            the instance being deleted (i.e., the user belongs to the Group
            associated with a given Dataset).  If set to False, the user will
            only be given permission to delete the instance if they also have
            the 'qcrbox.global_access' permission.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    obj_type = meta['obj_type']

    # If user is flagged as able to access unaffiliated data, always continue
    if request.user.has_perm('qcrbox.global_access'):
        pass

    # Allow for an access-point check if a user is affiliated with the company to which the data
    # pertains, to prevent users editing things they shouldnt
    elif not user_is_affiliated:
        LOGGER.info(
            'User %s denied permission to delete %s (pk=%d) (unaffiliated)',
            request.user.username,
            obj_type,
            obj_id,
        )
        raise PermissionDenied()

    try:
        instance = model.objects.get(pk=obj_id)

    except model.DoesNotExist:
        LOGGER.info(
            'User %s attempted to delete non-existent %s (pk=%d)',
            request.user.username,
            obj_type,
            obj_id,
        )
        messages.success(request, f'{obj_type} was deleted succesfully.')
        return redirect('view_'+meta['link_suffix'])

    instance_string = str(instance)
    instance.delete()

    LOGGER.info(
        'User %s deleted %s "%s"',
        request.user.username,
        obj_type,
        instance_string,
    )
    messages.success(request, f'{obj_type} "{instance_string}" was deleted succesfully!')
    return redirect('view_'+meta['link_suffix'])
