"""QCRBox URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from . import views
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.landing, name='landing'),
    path('workflow', views.initialise_workflow, name='initialise_workflow'),
    path('workflow/<file_id>', views.workflow, name='workflow'),
    path('download/<file_id>', views.download, name='download'),

    path('login', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),

    path('view_users', views.view_users, name='view_users'),
    path('create_user', views.create_user, name='create_user'),
    path('edit_user/<user_id>', views.update_user, name='edit_user'),
    path('delete_user/<user_id>', views.delete_user, name='delete_user'),

    path('create_group', views.create_group, name='create_group'),
    path('view_groups', views.view_groups, name='view_groups'),
    path('edit_group/<group_id>', views.update_group, name='edit_group'),
    path('delete_group/<group_id>', views.delete_group, name='delete_group'),

    path('view_datasets', views.view_datasets, name='view_datasets'),
    path('delete_dataset/<dataset_id>', views.delete_dataset, name='delete_dataset'),

    path('frontend_logs', views.frontend_logs, name='frontend_logs'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)