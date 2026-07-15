'''Unit tests for the QCrBox frontend's identity sync and workflow helpers.'''

from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import Group, User
from django.test import TestCase

from core.auth_backends import sync_user_groups
from qcrbox import forms
from qcrbox import models
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


class GetSessionGuiStatusTests(TestCase):
    '''Tests for the single-shot GUI status check behind the launch waiting
    page (which polls it from the browser while the session starts in a
    parallel request).'''

    _request_with_session = GetSessionGuiUrlTests._request_with_session
    _api_response = staticmethod(GetSessionGuiUrlTests._api_response)

    def test_pending_without_session_cookie(self):
        request = mock.Mock()
        request.session = {}
        self.assertEqual(workflow.get_session_gui_status(request), ('pending', None))

    def test_pending_while_session_cookie_unchanged_from_launch(self):
        # The launch request has not finished yet: the cookie still holds the
        # id known when the launch was initiated (possibly of an old session).
        request = self._request_with_session('qcrbox_calc_0xold')
        status, _ = workflow.get_session_gui_status(request, prev_session_id='qcrbox_calc_0xold')
        self.assertEqual(status, 'pending')

    def test_pending_while_session_record_unavailable(self):
        invalid = mock.Mock()
        invalid.is_valid = False
        with mock.patch('qcrbox.workflow.api.get_session') as get_session:
            get_session.return_value = invalid
            status, _ = workflow.get_session_gui_status(
                self._request_with_session('qcrbox_calc_0x1'), prev_session_id='qcrbox_calc_0xold'
            )
        self.assertEqual(status, 'pending')

    def test_ready_with_gui_url(self):
        with mock.patch('qcrbox.workflow.api.get_session') as get_session:
            get_session.return_value = self._api_response('https://dummy-gui-abc.gui.example.com/')
            status, url = workflow.get_session_gui_status(
                self._request_with_session('qcrbox_calc_0x1')
            )
        self.assertEqual(status, 'ready')
        self.assertEqual(url, 'https://dummy-gui-abc.gui.example.com/')

    def test_static_for_pool_containers(self):
        with mock.patch('qcrbox.workflow.api.get_session') as get_session:
            get_session.return_value = self._api_response(None)
            status, url = workflow.get_session_gui_status(
                self._request_with_session('qcrbox_calc_0x1')
            )
        self.assertEqual(status, 'static')
        self.assertIsNone(url)

    def test_status_endpoint_returns_json(self):
        user = User.objects.create_user(username='alice', password='pw')
        self.client.force_login(user)
        session = self.client.session
        session['session_id'] = 'qcrbox_calc_0x1'
        session.save()
        with mock.patch('qcrbox.workflow.api.get_session') as get_session:
            get_session.return_value = self._api_response('https://dummy-gui-abc.gui.example.com/')
            response = self.client.get('/workflow/gui-status', {'prev': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'status': 'ready', 'gui_url': 'https://dummy-gui-abc.gui.example.com/'},
        )


class DisableableSelectTests(TestCase):
    '''Tests for greying out unusable commands in the command dropdown.'''

    def setUp(self):
        self.app = models.Application.objects.create(          # pylint: disable=no-member
            name='Dummy', url='http://x', version='0.1.0', slug='dummy_cli', port=0, active=True,
        )
        self.runnable = models.AppCommand.objects.create(     # pylint: disable=no-member
            app=self.app, name='runnable_command', interactive=True,
        )
        self.blocked = models.AppCommand.objects.create(      # pylint: disable=no-member
            app=self.app, name='blocked_command', interactive=True,
        )

    def test_disabled_options_render_with_tooltip(self):
        form = forms.SelectCommandForm(
            disabled_commands={self.blocked.pk: 'Missing CIF entries: _cell.length_a'},
        )
        html = str(form)
        self.assertIn('disabled', html)
        self.assertIn('Missing CIF entries: _cell.length_a', html)
        # The runnable command's option is not disabled
        runnable_option = [line for line in html.split('<option') if f'value="{self.runnable.pk}"' in line][0]
        self.assertNotIn('disabled', runnable_option)

    def test_form_without_disabled_commands_is_unchanged(self):
        html = str(forms.SelectCommandForm())
        self.assertNotIn('disabled', html)


class GetDisabledCommandsTests(TestCase):
    '''Tests for mapping the registry's can-run response to frontend commands.'''

    def setUp(self):
        self.app = models.Application.objects.create(          # pylint: disable=no-member
            name='Dummy', url='http://x', version='0.1.0', slug='dummy_cli', port=0, active=True,
        )
        self.command = models.AppCommand.objects.create(      # pylint: disable=no-member
            app=self.app, name='change_cif_name', interactive=False,
        )
        self.load_file = mock.Mock()
        self.load_file.backend_uuid = 'qcrbox_ds_0x1'
        self.load_file.filename = 'test.cif'

    @staticmethod
    def _dataset_response(datafile_id):
        data_file = mock.Mock()
        data_file.qcrbox_file_id = datafile_id
        dataset = mock.Mock()
        dataset.data_files = {'test.cif': data_file}
        response = mock.Mock()
        response.is_valid = True
        response.body.payload.datasets = [dataset]
        return response

    @staticmethod
    def _runnable_response(commands):
        response = mock.Mock()
        response.is_valid = True
        response.body.payload.commands = commands
        return response

    def test_blocked_commands_are_mapped_to_pks_with_tooltips(self):
        status = SimpleNamespace(
            application_slug='dummy_cli', application_version='0.1.0',
            command_name='change_cif_name', can_run=False,
            missing_entries=['_cell.length_a'], reason=None,
        )
        with mock.patch('qcrbox.workflow.api.get_dataset') as get_dataset, \
             mock.patch('qcrbox.workflow.api.get_runnable_commands') as get_runnable:
            get_dataset.return_value = self._dataset_response('qcrbox_df_0x1')
            get_runnable.return_value = self._runnable_response([status])
            disabled = workflow.get_disabled_commands(self.load_file)
        self.assertEqual(disabled, {self.command.pk: 'Missing CIF entries: _cell.length_a'})
        get_runnable.assert_called_once_with('qcrbox_df_0x1')

    def test_runnable_and_unknown_commands_are_not_disabled(self):
        statuses = [
            SimpleNamespace(
                application_slug='dummy_cli', application_version='0.1.0',
                command_name='change_cif_name', can_run=True,
                missing_entries=[], reason=None,
            ),
            SimpleNamespace(
                application_slug='not_synced_app', application_version='9.9',
                command_name='whatever', can_run=False,
                missing_entries=['_x.y'], reason=None,
            ),
        ]
        with mock.patch('qcrbox.workflow.api.get_dataset') as get_dataset, \
             mock.patch('qcrbox.workflow.api.get_runnable_commands') as get_runnable:
            get_dataset.return_value = self._dataset_response('qcrbox_df_0x1')
            get_runnable.return_value = self._runnable_response(statuses)
            self.assertEqual(workflow.get_disabled_commands(self.load_file), {})

    def test_api_failures_fail_open(self):
        invalid = mock.Mock()
        invalid.is_valid = False
        with mock.patch('qcrbox.workflow.api.get_dataset') as get_dataset:
            get_dataset.return_value = invalid
            self.assertEqual(workflow.get_disabled_commands(self.load_file), {})

        with mock.patch('qcrbox.workflow.api.get_dataset') as get_dataset, \
             mock.patch('qcrbox.workflow.api.get_runnable_commands') as get_runnable:
            get_dataset.return_value = self._dataset_response('qcrbox_df_0x1')
            get_runnable.return_value = invalid
            self.assertEqual(workflow.get_disabled_commands(self.load_file), {})

    def test_reason_is_used_as_tooltip_when_no_missing_entries(self):
        status = SimpleNamespace(
            application_slug='dummy_cli', application_version='0.1.0',
            command_name='change_cif_name', can_run=False,
            missing_entries=[], reason='not a parseable CIF file',
        )
        with mock.patch('qcrbox.workflow.api.get_dataset') as get_dataset, \
             mock.patch('qcrbox.workflow.api.get_runnable_commands') as get_runnable:
            get_dataset.return_value = self._dataset_response('qcrbox_df_0x1')
            get_runnable.return_value = self._runnable_response([status])
            disabled = workflow.get_disabled_commands(self.load_file)
        self.assertEqual(disabled, {self.command.pk: 'not a parseable CIF file'})


class SaveDatasetMetadataTests(TestCase):
    '''Tests for typed-output capture in workflow.save_dataset_metadata.'''

    def setUp(self):
        self.user = User.objects.create(username='alice')
        self.group = Group.objects.create(name='TestGroup')
        self.app = models.Application.objects.create(          # pylint: disable=no-member
            name='Dummy', url='http://x', version='0.1.0', slug='dummy_cli', port=0, active=True,
        )
        self.command = models.AppCommand.objects.create(       # pylint: disable=no-member
            app=self.app, name='generate_report_artifacts', interactive=False,
        )
        self.infile = models.FileMetaData.objects.create(      # pylint: disable=no-member
            filename='in.cif', display_filename='in.cif', user=self.user,
            group=self.group, backend_uuid='qcrbox_ds_0xin', filetype='cif',
        )
        self.request = mock.Mock()
        self.request.user = self.user

    @staticmethod
    def _data_file(file_id, filename, filetype='cif', kind=None):
        data_file = mock.Mock()
        data_file.qcrbox_file_id = file_id
        data_file.filename = filename
        data_file.filetype = filetype
        data_file.kind = kind
        return data_file

    @classmethod
    def _dataset_response(cls, data_files):
        dataset = mock.Mock()
        dataset.qcrbox_dataset_id = 'qcrbox_ds_0xout'
        dataset.data_files.additional_properties = {df.filename: df for df in data_files}
        response = mock.Mock()
        response.is_valid = True
        response.body.payload.datasets = [dataset]
        return response

    def test_primary_is_the_kindless_file_not_the_first(self):
        response = self._dataset_response([
            self._data_file('df1', 'report.txt', 'txt', kind='text'),
            self._data_file('df2', 'result.cif', 'cif', kind=None),
        ])
        newfile, step = workflow.save_dataset_metadata(
            self.request, response, self.group, infile=self.infile, command=self.command,
        )
        self.assertEqual(newfile.filename, 'result.cif')
        self.assertEqual(step.outfile, newfile)
        artifacts = list(step.artifacts.all())
        self.assertEqual([(a.kind, a.filename, a.data_file_id) for a in artifacts],
                         [('text', 'report.txt', 'df1')])

    def test_artifact_only_dataset_creates_step_without_outfile(self):
        response = self._dataset_response([
            self._data_file('df1', 'report.txt', 'txt', kind='text'),
            self._data_file('df2', 'graph.json', 'json', kind='interactive_graph'),
        ])
        newfile, step = workflow.save_dataset_metadata(
            self.request, response, self.group, infile=self.infile, command=self.command,
        )
        self.assertIsNone(newfile)
        self.assertIsNone(step.outfile)
        self.assertEqual(step.infile, self.infile)
        self.assertEqual(step.artifacts.count(), 2)

    def test_plain_upload_returns_file_and_no_step(self):
        response = self._dataset_response([self._data_file('df1', 'upload.cif')])
        newfile, step = workflow.save_dataset_metadata(self.request, response, self.group)
        self.assertEqual(newfile.filename, 'upload.cif')
        self.assertIsNone(step)

    def test_kind_from_additional_properties_fallback(self):
        legacy_file = mock.Mock(spec=['qcrbox_file_id', 'filename', 'filetype', 'additional_properties'])
        legacy_file.qcrbox_file_id = 'df1'
        legacy_file.filename = 'report.txt'
        legacy_file.filetype = 'txt'
        legacy_file.additional_properties = {'kind': 'text'}
        response = self._dataset_response([legacy_file])
        newfile, step = workflow.save_dataset_metadata(
            self.request, response, self.group, infile=self.infile, command=self.command,
        )
        self.assertIsNone(newfile)
        self.assertEqual(step.artifacts.first().kind, 'text')
