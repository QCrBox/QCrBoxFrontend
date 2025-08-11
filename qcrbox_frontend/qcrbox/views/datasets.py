'''QCrBox Datasets

Module containing the view methods which generate and serve http responses to
the browser when their related url is accessed.

Contains views pertaining to Dataset management and Data Dashboard-related
views.

'''

import logging

from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required
from django.http import HttpResponse

from qcrbox import api, models
from qcrbox.plotly_dash import plotly_app                           # pylint: disable=unused-import
from qcrbox.utility import check_user_view_file_permission, DisplayField, paginate_objects

LOGGER = logging.getLogger(__name__)


@login_required(login_url='login')
def history_dashboard(request, dataset_id):
    '''A view to handle rendering the page containing the Tree Dashboard
    showing dataset ancestry.

    '''

    return render(request, 'history_dashboard.html', {
        'wide_layout' : True,
        'dash_context' : {'init_pk':{'title':dataset_id}}
    })

# No view for dataset creation (handled through the workflow initialisation page)

@login_required(login_url='login')
def view_datasets(request):
    '''A view to handle generating and rendering the 'view datasets list'
    page.  The contents of this page are filtered based on the request user's
    permissions and are paginated.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    fields = [
        DisplayField('Filename', 'display_filename', is_header=True),
        DisplayField('Group', 'group'),
        DisplayField('Created By', 'user'),
        DisplayField('At Time', 'creation_time'),
        DisplayField('From File', 'created_from', is_special=True),
        DisplayField('With App', 'created_app', is_special=True),
        ]

    object_list = models.FileMetaData.objects.filter(active=True)       # pylint: disable=no-member

    # If a user can view unaffiliated data, they can view it all
    if request.user.has_perm('qcrbox.global_access'):
        pass
    else:
        object_list = object_list.filter(group__in=request.user.groups.all())

    object_list = object_list.order_by('group__name', 'filename')
    page = request.GET.get('page')

    objects = paginate_objects(object_list, page)

    return render(request, 'view_list_generic.html', {
        'objects': objects,
        'type':'Dataset',
        'fields':fields,
        'edit_perms':request.user.has_perm('qcrbox.edit_data'),
        'delete_link':'delete_dataset',
        'history_link':'dataset_history',
    })

@permission_required('qcrbox.edit_data', raise_exception=True)
def delete_dataset(request, dataset_id):
    '''A view to handle sending a 'delete dataset' command to the API and, if
    succesful, flag the Frontend db entry for that dataset as inactive.  This
    does not actually delete any information from the Frontend DB, such that
    the modification history of datasets can be preserved, but disables some
    functionality (e.g. the ability to download or start a workflow) for
    datasets marked as inactive in this way.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - dataset_id(int): the Frontend db primary key of the dataset being
            deleted.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url.

    '''

    deletion_data_meta = models.FileMetaData.objects.get(pk=dataset_id) # pylint: disable=no-member

    # Check credentials before invoking the generic delete, as API will also need calling
    check_user_view_file_permission(request.user, deletion_data_meta)

    LOGGER.info(
        'User %s deleting dataset %s',
        request.user.username,
        deletion_data_meta.display_filename,
    )
    api.get_dataset(deletion_data_meta.backend_uuid)
    api_response = api.delete_dataset(deletion_data_meta.backend_uuid)

    if not api_response.is_valid:
        LOGGER.warning('Delete request unsuccessful!')

        # Check if file is also missing from the backend
        get_response = api.get_dataset(deletion_data_meta.backend_uuid)
        if not (get_response.is_valid) and get_response.body.error.code == 404:
            LOGGER.info('Dataset already absent from backend; marking as deleted')

        else:
            # Otherwise, error out; delete unsuccesful
            messages.warning(request, 'API delete request unsuccessful: file not deleted!')
            return redirect('view_datasets')

    try:
        instance = models.FileMetaData.objects.get(pk=dataset_id)       # pylint: disable=no-member

    except models.FileMetaData.DoesNotExist:                            # pylint: disable=no-member
        LOGGER.info(
            'User %s attempted to deactivate non-existent File Metadata (pk=%d)',
            request.user.username,
            dataset_id,
        )
        messages.success(request, 'Dataset was deleted successfully.')
        return redirect('view_datasets')

    # Don't actually delete the local metadata, just flag it as inactive so history can be preserved
    instance.active = False
    instance.save()

    LOGGER.info(
        'User %s flagged File Metadata "%s" as inactive.',
        request.user.username,
        instance.display_filename,
    )
    messages.success(request, f'Dataset "{instance}" was deleted successfully!')
    return redirect('view_datasets')

@login_required(login_url='login')
def download(request, file_id):
    '''A view to handle fetching the contents of datasets from the Backend
    and serving them to the user as a download.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - file_id(int): the Frontend db primary key of the dataset being
            downloaded.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url, containing the download
            file.

    '''

    # Fetch the metadata
    download_file_meta = models.FileMetaData.objects.get(pk=file_id)    # pylint: disable=no-member

    # Stop user accessing data from a group they have no access to
    check_user_view_file_permission(request.user, download_file_meta)

    LOGGER.info(
        'User %s downloading dataset "%s"',
        request.user.username,
        download_file_meta.display_filename,
    )
    api_response = api.download_dataset(download_file_meta.backend_uuid)

    if not api_response.is_valid:
        messages.warning(request, 'Could not fetch the requested file!')
        LOGGER.error('Could not find requested dataset!')
        return redirect('initialise_workflow')

    data = api_response.body

    # Deliver the file using the filename stored in metadata
    httpresponse = HttpResponse(data)
    d_filename = download_file_meta.display_filename
    httpresponse['Content-Disposition'] = 'attachment; filename=' + d_filename
    return httpresponse

@login_required(login_url='login')
def visualise(request, dataset_id):
    '''A view to handle calling the qcrbox_quality visualiser app and opening
    a given file to view with it.

    Parameters:
    - request(WSGIRequest): the request from a user which triggers a url
            associated to this view.
    - dataset_id(int): the Frontend db primary key of the dataset being
            visualised.

    Returns:
    - response(HttpResponse): the http response served to the user on
            accessing this view's associated url, containing the redirect to
            the visualiser.

    '''

    # Fetch the metadata
    visualise_file_meta = models.FileMetaData.objects.get(pk=dataset_id)# pylint: disable=no-member

    # Stop user accessing data from a group they have no access to
    check_user_view_file_permission(request.user, visualise_file_meta)

    # Get host name without port, manually prepend http:// to stop django
    # treating this as a relative URL
    hostname = 'http://' + request.get_host().split(':')[0]
    v_url = f'{hostname}:{settings.API_VISUALISER_PORT}/retrieve/{visualise_file_meta.backend_uuid}'
    LOGGER.info(
        'Opening Visualiser at "%s"',
        v_url,
    )

    return redirect(v_url)
