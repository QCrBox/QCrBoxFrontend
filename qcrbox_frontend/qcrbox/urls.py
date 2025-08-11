'''QCRBox URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
'''

from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from qcrbox.views import datasets, debug, groups, users, workflows

urlpatterns = [
    path('', workflows.landing, name='landing'),
    path('workflow', workflows.initialise_workflow, name='initialise_workflow'),
    path('workflow/<file_id>', workflows.workflow, name='workflow'),
    path(
        'workflow/<file_id>/pending/<command_id>',
        workflows.workflow_pending,
        name='workflow-pending',
    ),
    path('download/<file_id>', datasets.download, name='download'),

    path('login', users.login_view, name='login'),
    path('logout', users.logout_view, name='logout'),

    path('view_users', users.view_users, name='view_users'),
    path('create_user', users.create_user, name='create_user'),
    path('edit_user/<user_id>', users.update_user, name='edit_user'),
    path('edit_account/', users.edit_user, name='edit_account'),
    path('edit_password/', users.update_password, name='edit_password'),
    path('delete_user/<user_id>', users.delete_user, name='delete_user'),

    path('create_group', groups.create_group, name='create_group'),
    path('view_groups', groups.view_groups, name='view_groups'),
    path('edit_group/<group_id>', groups.update_group, name='edit_group'),
    path('delete_group/<group_id>', groups.delete_group, name='delete_group'),

    path('data_history/<dataset_id>', datasets.history_dashboard, name='dataset_history'),
    path('view_datasets', datasets.view_datasets, name='view_datasets'),
    path('delete_dataset/<dataset_id>', datasets.delete_dataset, name='delete_dataset'),
    path('visualise/<dataset_id>', datasets.visualise, name='visualise'),

    path('frontend_logs', debug.frontend_logs, name='frontend_logs'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
