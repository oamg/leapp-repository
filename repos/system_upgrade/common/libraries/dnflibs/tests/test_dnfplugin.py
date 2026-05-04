import os
from unittest.mock import MagicMock

import pytest

from leapp.libraries.common.dnflibs import dnfplugin
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import DNFWorkaround, Module


class MockContext:
    def __init__(self, should_raise=None):
        self.should_raise = should_raise
        self.makedirs_calls = []
        self.open_calls = []
        self.copy_from_calls = []
        self.copytree_from_calls = []
        self.call_calls = []
        self._files = {}

    def makedirs(self, path, exists_ok=False):
        self.makedirs_calls.append((path, exists_ok))

    def open(self, path, mode):
        self.open_calls.append((path, mode))
        mock_file = MagicMock()
        self._files[path] = mock_file
        return mock_file

    def copy_from(self, src, dst):
        self.copy_from_calls.append((src, dst))

    def copytree_from(self, src, dst):
        self.copytree_from_calls.append((src, dst))
        if self.should_raise:
            raise self.should_raise

    def call(self, cmd, **kwargs):
        self.call_calls.append(cmd)
        if self.should_raise:
            raise self.should_raise


class MockTasks:
    def __init__(self):
        self.local_rpms = ['/path/to/rpm1.rpm', '/path/to/rpm2.rpm']
        self.to_install = ['pkg1', 'pkg2']
        self.to_remove = ['old-pkg1', 'old-pkg2']
        self.to_upgrade = ['upgrade-pkg1', 'upgrade-pkg2']
        self.modules_to_enable = []
        self.modules_to_reset = []


@pytest.mark.parametrize('target_version', ['9', '10'])
def test_install_success(monkeypatch, leapp_tmpdir, target_version):
    target_basedir = leapp_tmpdir

    monkeypatch.setattr(dnfplugin, 'get_target_major_version', lambda: target_version)

    plugin_source = os.path.join(leapp_tmpdir, 'source', dnfplugin.DNF_PLUGIN_NAME)
    os.makedirs(os.path.dirname(plugin_source), exist_ok=True)
    with open(plugin_source, 'w') as f:
        f.write('# DNF plugin')

    monkeypatch.setattr(api, 'get_file_path', lambda name: plugin_source)

    target_plugin_dir = os.path.join(
        target_basedir,
        dnfplugin._DNF_PLUGIN_PATHS[target_version].lstrip('/')
    )
    os.makedirs(os.path.dirname(target_plugin_dir), exist_ok=True)

    dnfplugin.install(target_basedir)

    target_plugin_path = os.path.join(os.path.dirname(target_plugin_dir), dnfplugin.DNF_PLUGIN_NAME)
    assert os.path.exists(target_plugin_path)


def test_install_failure(monkeypatch, leapp_tmpdir):
    target_basedir = leapp_tmpdir

    monkeypatch.setattr(dnfplugin, 'get_target_major_version', lambda: '9')
    monkeypatch.setattr(api, 'get_file_path', lambda name: '/nonexistent/file')
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    with pytest.raises(dnfplugin.DNFPluginInstallError) as exc_info:
        dnfplugin.install(target_basedir)

    assert 'Failed to install DNF plugin' in str(exc_info.value)


def test_install_unsupported_version(monkeypatch, leapp_tmpdir):
    target_basedir = leapp_tmpdir

    monkeypatch.setattr(dnfplugin, 'get_target_major_version', lambda: '99')

    with pytest.raises(KeyError):
        dnfplugin.install(target_basedir)


@pytest.mark.parametrize('debug,test,on_aws', [
    (True, False, False),
    (False, True, True),
    (True, True, False),
])
def test_build_plugin_data(monkeypatch, debug, test, on_aws):
    tasks = MockTasks()
    module1 = Module(name='nodejs', stream='18')
    module2 = Module(name='postgresql', stream='15')
    tasks.modules_to_enable = [module1, module2]

    target_repoids = ['rhel-9-baseos', 'rhel-9-appstream']

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='9.3'))
    monkeypatch.setattr(dnfplugin, 'is_nogpgcheck_set', lambda: False)

    data = dnfplugin.build_plugin_data(target_repoids, debug, test, tasks, on_aws)

    assert data['pkgs_info']['local_rpms'] == ['/installroot/path/to/rpm1.rpm', '/installroot/path/to/rpm2.rpm']
    assert data['pkgs_info']['to_install'] == ['pkg1', 'pkg2']
    assert data['pkgs_info']['to_remove'] == ['old-pkg1', 'old-pkg2']
    assert data['pkgs_info']['to_upgrade'] == ['upgrade-pkg1', 'upgrade-pkg2']
    assert 'nodejs:18' in data['pkgs_info']['modules_to_enable']
    assert 'postgresql:15' in data['pkgs_info']['modules_to_enable']

    assert data['dnf_conf']['debugsolver'] is debug
    assert data['dnf_conf']['enable_repos'] == target_repoids
    assert data['dnf_conf']['platform_id'] == 'platform:el9'
    assert data['dnf_conf']['releasever'] == '9.3'
    assert data['dnf_conf']['test_flag'] is test
    assert data['dnf_conf']['gpgcheck'] is True

    assert data['rhui']['aws']['on_aws'] is on_aws


def test_build_plugin_data_with_nogpgcheck(monkeypatch):
    tasks = MockTasks()

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='9.3'))
    monkeypatch.setattr(dnfplugin, 'is_nogpgcheck_set', lambda: True)

    data = dnfplugin.build_plugin_data([], False, False, tasks, False)

    assert data['dnf_conf']['gpgcheck'] is False


def test_create_config(monkeypatch):
    context = MockContext()
    tasks = MockTasks()
    target_repoids = ['repo1', 'repo2']

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='9.3'))
    monkeypatch.setattr(dnfplugin, 'is_nogpgcheck_set', lambda: False)

    dnfplugin.create_config(context, target_repoids, debug=True, test=False, tasks=tasks, on_aws=False)

    assert len(context.makedirs_calls) == 1
    assert context.makedirs_calls[0][0] == os.path.dirname(dnfplugin.DNF_PLUGIN_DATA_PATH)

    assert len(context.open_calls) == 1
    assert context.open_calls[0][0] == dnfplugin.DNF_PLUGIN_DATA_PATH
    assert context.open_calls[0][1] == 'w+'


def test_backup_config():
    context = MockContext()

    dnfplugin.backup_config(context)

    assert len(context.copy_from_calls) == 1
    assert context.copy_from_calls[0] == (dnfplugin.DNF_PLUGIN_DATA_PATH, dnfplugin.DNF_PLUGIN_DATA_LOG_PATH)


def test_backup_debug_data_with_debug(monkeypatch):
    context = MockContext()

    monkeypatch.setattr(dnfplugin.config, 'is_debug', lambda: True)

    dnfplugin.backup_debug_data(context)

    assert len(context.copytree_from_calls) == 1
    assert context.copytree_from_calls[0][0] == '/debugdata'


def test_backup_debug_data_without_debug(monkeypatch):
    context = MockContext()

    monkeypatch.setattr(dnfplugin.config, 'is_debug', lambda: False)

    dnfplugin.backup_debug_data(context)

    assert len(context.copytree_from_calls) == 0


def test_backup_debug_data_oserror(monkeypatch):
    context = MockContext(should_raise=OSError('Permission denied'))

    monkeypatch.setattr(dnfplugin.config, 'is_debug', lambda: True)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    dnfplugin.backup_debug_data(context)


@pytest.mark.parametrize('stderr,is_container,expected_in_message', [
    ('At least 500MB more space needed on the / filesystem.', True, '500MB'),
    ('At least 500MB more space needed on the /usr filesystem.', False, '/usr'),
    ('At least 200MB more space needed on the /var filesystem.', False, '/var'),
])
def test_handle_transaction_err_msg_no_space(stderr, is_container, expected_in_message):
    err = CalledProcessError(
        'dnf failed',
        ['dnf', 'upgrade'],
        {
            'stdout': 'stdout',
            'stderr': 'Error: Transaction test error:\n  Disk Requirements:\n    {}'.format(stderr),
            'exit_code': 1
        }
    )

    with pytest.raises(dnfplugin.DNFUpgradeTransactionError) as exc_info:
        dnfplugin._handle_transaction_err_msg(err, is_container=is_container)

    assert 'not enough space' in str(exc_info.value).lower()
    hint = str(exc_info.value.details.get('hint', ''))
    disk_reqs = str(exc_info.value.details.get('Disk Requirements', ''))
    assert expected_in_message in (hint + disk_reqs)


def test_handle_transaction_err_msg_generic_error():
    err = CalledProcessError(
        'dnf failed',
        ['dnf', 'upgrade'],
        {'stdout': 'stdout output', 'stderr': 'Some other DNF error', 'exit_code': 1}
    )

    with pytest.raises(dnfplugin.DNFUpgradeTransactionError) as exc_info:
        dnfplugin._handle_transaction_err_msg(err, is_container=False)

    assert 'DNF execution failed' in str(exc_info.value)
    assert exc_info.value.details['STDOUT'] == 'stdout output'
    assert exc_info.value.details['STDERR'] == 'Some other DNF error'
    assert 'proxy' in exc_info.value.details['hint'].lower()


def test_apply_workarounds_success(monkeypatch):
    workaround1 = DNFWorkaround(
        display_name='Workaround 1',
        script_path='/path/to/script1.sh',
        script_args=[]
    )
    workaround2 = DNFWorkaround(
        display_name='Workaround 2',
        script_path='/path/to/script2.sh',
        script_args=['arg1', 'arg2']
    )

    context = MockContext()

    monkeypatch.setattr(api, 'consume', lambda model: [workaround1, workaround2])
    monkeypatch.setattr(api, 'show_message', lambda msg: None)

    dnfplugin.apply_workarounds(context)

    assert len(context.call_calls) == 2
    assert context.call_calls[0] == ['/bin/bash', '-c', '/path/to/script1.sh']
    assert context.call_calls[1] == ['/bin/bash', '-c', '/path/to/script2.sh arg1 arg2']


def test_apply_workarounds_script_fails(monkeypatch):
    workaround = DNFWorkaround(
        display_name='Failing Workaround',
        script_path='/path/to/failing.sh',
        script_args=[]
    )

    context = MockContext(should_raise=CalledProcessError(
        'Script failed',
        ['/bin/bash', '-c', '/path/to/failing.sh'],
        {'exit_code': 1, 'stdout': '', 'stderr': 'Script error'}
    ))

    monkeypatch.setattr(api, 'consume', lambda model: [workaround])
    monkeypatch.setattr(api, 'show_message', lambda msg: None)

    with pytest.raises(dnfplugin.RegisteredWorkaroundApplicationError) as exc_info:
        dnfplugin.apply_workarounds(context)

    assert 'Failed to execute script' in str(exc_info.value)
    assert 'Failing Workaround' in exc_info.value.details['workaround name']
