'''Unit tests for the QCrBox frontend's identity sync and workflow helpers.'''

from unittest import mock

from django.contrib.auth.models import Group, User
from django.test import TestCase

from core.auth_backends import sync_user_groups
from qcrbox import workflow


class SyncUserGroupsTests(TestCase):
    '''Tests for mirroring group membership from the Remote-Groups header.'''

    def setUp(self):
        self.user = User.objects.create_user(username='alice')

    def test_groups_are_created_and_assigned(self):
        sync_user_groups(self.user, 'crystallography, chemistry')
        self.assertEqual(
            sorted(self.user.groups.values_list('name', flat=True)),
            ['chemistry', 'crystallography'],
        )

    def test_memberships_are_replaced_not_accumulated(self):
        sync_user_groups(self.user, 'old_group')
        sync_user_groups(self.user, 'new_group')
        self.assertEqual(list(self.user.groups.values_list('name', flat=True)), ['new_group'])
        # The group itself is never deleted (dataset ACLs may reference it)
        self.assertTrue(Group.objects.filter(name='old_group').exists())

    def test_lldap_internal_groups_are_not_mirrored(self):
        sync_user_groups(self.user, 'lldap_admin, lldap_password_manager, science')
        self.assertEqual(list(self.user.groups.values_list('name', flat=True)), ['science'])
        self.assertFalse(Group.objects.filter(name='lldap_admin').exists())

    def test_role_groups_grant_permissions(self):
        sync_user_groups(self.user, 'qcrbox_global_managers')
        self.user = User.objects.get(pk=self.user.pk)  # clear permission cache
        self.assertTrue(self.user.has_perm('qcrbox.edit_users'))
        self.assertTrue(self.user.has_perm('qcrbox.edit_data'))
        self.assertTrue(self.user.has_perm('qcrbox.global_access'))

        sync_user_groups(self.user, 'qcrbox_group_managers')
        group = Group.objects.get(name='qcrbox_group_managers')
        self.user = User.objects.get(pk=self.user.pk)
        self.assertTrue(self.user.has_perm('qcrbox.edit_users'))
        self.assertFalse(self.user.has_perm('qcrbox.global_access'))
        self.assertEqual(
            sorted(group.permissions.values_list('codename', flat=True)),
            ['edit_data', 'edit_users'],
        )

    def test_empty_header_clears_memberships(self):
        sync_user_groups(self.user, 'science')
        sync_user_groups(self.user, '')
        self.assertEqual(self.user.groups.count(), 0)


class GetSessionGuiUrlTests(TestCase):
    '''Tests for fetching the per-instance GUI URL of an open session.'''

    def _request_with_session(self, session_id):
        request = mock.Mock()
        request.session = {'session_id': session_id}
        return request

    @staticmethod
    def _api_response(gui_url):
        session_info = mock.Mock()
        session_info.additional_properties = {'gui_url': gui_url} if gui_url else {}
        response = mock.Mock()
        response.is_valid = True
        response.body.payload.interactive_sessions = [session_info]
        return response

    def test_returns_gui_url_when_available(self):
        with mock.patch('qcrbox.workflow.api.get_session') as get_session:
            get_session.return_value = self._api_response('https://dummy-gui-abc.gui.example.com/')
            url = workflow.get_session_gui_url(self._request_with_session('qcrbox_calc_0x1'))
        self.assertEqual(url, 'https://dummy-gui-abc.gui.example.com/')

    def test_returns_typed_gui_url_of_newer_api_clients(self):
        # API clients regenerated after the field was added expose gui_url as
        # a typed attribute instead of via additional_properties.
        response = self._api_response(None)
        session_info = response.body.payload.interactive_sessions[0]
        session_info.gui_url = 'https://dummy-gui-typed.gui.example.com/'
        with mock.patch('qcrbox.workflow.api.get_session') as get_session:
            get_session.return_value = response
            url = workflow.get_session_gui_url(self._request_with_session('qcrbox_calc_0x1'))
        self.assertEqual(url, 'https://dummy-gui-typed.gui.example.com/')

    def test_returns_none_for_static_containers(self):
        with mock.patch('qcrbox.workflow.api.get_session') as get_session:
            get_session.return_value = self._api_response(None)
            url = workflow.get_session_gui_url(
                self._request_with_session('qcrbox_calc_0x1'), max_attempts=1
            )
        self.assertIsNone(url)

    def test_returns_none_without_session_cookie(self):
        request = mock.Mock()
        request.session = {}
        self.assertIsNone(workflow.get_session_gui_url(request))

    def test_retries_until_session_record_appears(self):
        invalid = mock.Mock()
        invalid.is_valid = False
        with mock.patch('qcrbox.workflow.api.get_session') as get_session:
            get_session.side_effect = [invalid, self._api_response('https://x.gui.example.com/')]
            url = workflow.get_session_gui_url(
                self._request_with_session('qcrbox_calc_0x1'), max_attempts=2, retry_delay=0
            )
        self.assertEqual(url, 'https://x.gui.example.com/')
        self.assertEqual(get_session.call_count, 2)
