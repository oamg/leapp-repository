import enum
import functools
import grp
import os
from collections import namedtuple

import pytest

from leapp.libraries.actor import prepareliveimage as modify_userspace_for_livemode_lib
from leapp.libraries.common import mounting
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import FstabEntry, LiveModeConfig, StorageInfo, TargetUserSpaceInfo

_LiveModeConfig = functools.partial(LiveModeConfig, squashfs_fullpath='<squashfs-path>')


@pytest.mark.parametrize(
    ('livemode_config', 'should_modify'),
    (
        (_LiveModeConfig(is_enabled=True), True,),
        (_LiveModeConfig(is_enabled=False), False,),
        (None, False)
    )
)
def test_modifications_require_livemode_enabled(monkeypatch, livemode_config, should_modify):
    monkeypatch.setattr(api, 'produce', produce_mocked())

    class NspawnActionsMock(object):
        def __init__(self, *arg, **kwargs):
            pass

        def __enter__(self):
            pass

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(mounting, 'NspawnActions', NspawnActionsMock)

    modification_fns = [
        'setup_upgrade_service',
        'setup_console',
        'setup_sshd',
        'create_fstab_mounting_current_root_elsewhere',
        'create_symlink_from_sysroot_to_source_root_mountpoint',
        'make_root_account_passwordless',
        'create_etc_issue',
        'enable_dbus',
        'setup_network',
        'fakerootfs'
    ]

    def do_nothing(call_list, called_fn, *args, **kwargs):
        call_list.append(called_fn)

    call_list = []
    for modification_fn in modification_fns:
        monkeypatch.setattr(modify_userspace_for_livemode_lib, modification_fn,
                            functools.partial(do_nothing, call_list, modification_fn))

    userspace = TargetUserSpaceInfo(path='<userspace-path>', scratch='<scratch-path>', mounts='<mounts-dir>')
    storage = StorageInfo()

    modify_userspace_for_livemode_lib.modify_userspace_as_configured(userspace, storage, livemode_config)

    if should_modify:
        assert 'setup_upgrade_service' in call_list
    else:
        assert not call_list


Action = namedtuple('Action', ('type_', 'args'))


class ActionType(enum.Enum):
    COPY = 0
    SYMLINK = 1
    OPEN = 2
    WRITE = 3
    CHOWN = 4
    CHMOD = 5


class WriterMock(object):
    def __init__(self, action_log):
        self.action_log = action_log

    def write(self, content):
        action = Action(type_=ActionType.WRITE, args=(content,))
        self.action_log.append(action)


class FileHandleMock(object):
    def __init__(self, action_log):
        self.action_log = action_log

    def __enter__(self):
        return WriterMock(action_log=self.action_log)

    def __exit__(self, *args):
        pass


class NspawnActionsMock(object):
    def __init__(self, base_dir, action_log):
        self.base_dir = base_dir
        self.action_log = action_log

    def copy_to(self, host_path, guest_path):
        self.action_log.append(Action(type_=ActionType.COPY, args=(host_path, self.full_path(guest_path))))

    def full_path(self, guest_path):
        abs_guest_path = os.path.abspath(guest_path)
        return os.path.join(self.base_dir, abs_guest_path.lstrip('/'))

    def open(self, guest_path, mode):
        host_path = self.full_path(guest_path)
        self.action_log.append(Action(type_=ActionType.OPEN, args=(host_path,)))
        return FileHandleMock(action_log=self.action_log)

    def makedirs(self, *args, **kwargs):
        pass


def assert_execution_trace_subsumes_other(actual_trace, expected_trace):
    expected_action_log_idx = 0
    for actual_action in actual_trace:
        if expected_trace[expected_action_log_idx] == actual_action:
            expected_action_log_idx += 1

        if expected_action_log_idx >= len(expected_trace):
            break

    if expected_action_log_idx < len(expected_trace):
        error_msg = 'Failed to find action {0} in actual action log'.format(
            expected_trace[expected_action_log_idx]
        )
        return error_msg
    return None


def test_setup_upgrade_service(monkeypatch):
    """
    Test whether setup_upgrade_service is being set up.

    The upgrade service is set up if:
    1) a service file is copied /usr/lib/systemd/system
    2) a shellscript /usr/bin/upgrade is copied into the userspace
    3) a symlink from /usr/lib/systemd/system/<service_file> to /etc/.../multi-user.target.wants/ is created
    """

    mocked_actor = CurrentActorMocked()
    monkeypatch.setattr(api, 'current_actor', mocked_actor)

    actual_trace = []
    context_mock = NspawnActionsMock('/USERSPACE', action_log=actual_trace)

    def symlink_mock(link_target, symlink_location):
        actual_trace.append(Action(type_=ActionType.SYMLINK, args=(link_target, symlink_location)))

    monkeypatch.setattr(os, 'symlink', symlink_mock)
    monkeypatch.setattr(os.path, 'exists', lambda path: False)

    modify_userspace_for_livemode_lib.setup_upgrade_service(context_mock)

    service_filename = modify_userspace_for_livemode_lib.LEAPP_UPGRADE_SERVICE_FILE
    expected_action_log = [
        Action(type_=ActionType.COPY,
               args=(os.path.join('files', service_filename),
                     os.path.join('/USERSPACE/usr/lib/systemd/system', service_filename))),
        Action(type_=ActionType.COPY,
               args=(os.path.join('files', 'do-upgrade.sh'), '/USERSPACE/usr/bin/upgrade')),
        Action(type_=ActionType.SYMLINK,
               args=(os.path.join('/usr/lib/systemd/system', service_filename),
                     os.path.join('/USERSPACE/etc/systemd/system/multi-user.target.wants', service_filename)))
    ]

    error = assert_execution_trace_subsumes_other(actual_trace, expected_action_log)
    assert not error, error


def test_setup_console(monkeypatch):
    """
    Test whether the console is being set up.

    The upgrade service is set up if:
    1) a consoele service file is copied /usr/lib/systemd/system
    2) /etc/systemd/login.d is modified
    3) old '/etc/systemd/system/getty.target.wants/getty@tty{tty_num}.service' is removed if it exists
    4) tty{2..5} are added to getty.target.wants
    5) leapp's console service is enabled
    """
    mocked_actor = CurrentActorMocked()
    monkeypatch.setattr(api, 'current_actor', mocked_actor)

    service_filename = modify_userspace_for_livemode_lib.LEAPP_CONSOLE_SERVICE_FILE
    expected_trace = [
        Action(type_=ActionType.COPY,
               args=(os.path.join('files', service_filename),
                     os.path.join('/USERSPACE/usr/lib/systemd/system', service_filename))),
        Action(type_=ActionType.OPEN, args=('/USERSPACE/etc/systemd/logind.conf',)),
        Action(type_=ActionType.WRITE, args=('NAutoVTs=1\n',)),
        Action(type_=ActionType.SYMLINK,
               args=('/usr/lib/systemd/system/getty@.service',
                     '/USERSPACE/etc/systemd/system/getty.target.wants/getty@tty2.service')),
        Action(type_=ActionType.SYMLINK,
               args=('/usr/lib/systemd/system/getty@.service',
                     '/USERSPACE/etc/systemd/system/getty.target.wants/getty@tty3.service')),
        Action(type_=ActionType.SYMLINK,
               args=('/usr/lib/systemd/system/getty@.service',
                     '/USERSPACE/etc/systemd/system/getty.target.wants/getty@tty4.service')),
        Action(type_=ActionType.SYMLINK,
               args=(os.path.join('/usr/lib/systemd/system/', service_filename),
                     os.path.join('/USERSPACE/etc/systemd/system/multi-user.target.wants/', service_filename))),
    ]

    actual_trace = []

    def symlink_mock(link_target, symlink_location):
        actual_trace.append(Action(type_=ActionType.SYMLINK, args=(link_target, symlink_location)))

    monkeypatch.setattr(os, 'symlink', symlink_mock)
    monkeypatch.setattr(os.path, 'exists', lambda path: False)

    context_mock = NspawnActionsMock(base_dir='/USERSPACE', action_log=actual_trace)
    modify_userspace_for_livemode_lib.setup_console(context_mock)

    error_str = assert_execution_trace_subsumes_other(actual_trace, expected_trace)
    assert not error_str, error_str


def test_setup_sshd(monkeypatch):
    """

    Test whether the sshd is set up correctly.

    SSHD setup should include:
    1) copying of any ssh_key_* and *.pub keys with correct rights, uid, gid into /etc/ssh
    2) copying the given config.setup_opensshd_with_auth_keys into /root/.ssh/authorized_keys with correct rights
    3) sshd is enabled
    """
    mocked_actor = CurrentActorMocked()
    monkeypatch.setattr(api, 'current_actor', mocked_actor)

    actual_trace = []

    def chmod_mock(path, rights):
        actual_trace.append(Action(type_=ActionType.CHMOD, args=(path, rights, )))

    def chown_mock(path, uid=None, gid=None):
        assert uid is not None
        assert gid is not None
        actual_trace.append(Action(type_=ActionType.CHOWN, args=(path, uid, gid)))

    def listdir_mock(path):
        assert path == '/etc/ssh'
        return [
            'ssh_key_A',
            'ssh_key_B',
            'ssh_key_A.pub'
        ]

    def symlink_mock(link_target, symlink_location):
        actual_trace.append(Action(type_=ActionType.SYMLINK, args=(link_target, symlink_location)))

    _GroupInfo = namedtuple('GroupInfo', ('gr_gid'))
    user_groups_table = {
        'root': _GroupInfo(0),
        'ssh_keys': _GroupInfo(1)
    }

    monkeypatch.setattr(os.path, 'exists', lambda *args, **kwargs: False)
    monkeypatch.setattr(os, 'chmod', chmod_mock)
    monkeypatch.setattr(os, 'chown', chown_mock)
    monkeypatch.setattr(os, 'symlink', symlink_mock)
    monkeypatch.setattr(os, 'listdir', listdir_mock)
    monkeypatch.setattr(grp, 'getgrnam', user_groups_table.get)

    context_mock = NspawnActionsMock(base_dir='/USERSPACE', action_log=actual_trace)

    modify_userspace_for_livemode_lib.setup_sshd(context_mock, 'AUTHORIZED_KEYS')

    expected_trace = [
        Action(type_=ActionType.COPY, args=('/etc/ssh/ssh_key_A', '/USERSPACE/etc/ssh')),
        Action(type_=ActionType.CHMOD, args=('/USERSPACE/etc/ssh/ssh_key_A', 0o640)),
        Action(type_=ActionType.CHOWN, args=('/USERSPACE/etc/ssh/ssh_key_A', 0, 1)),
        Action(type_=ActionType.COPY, args=('/etc/ssh/ssh_key_B', '/USERSPACE/etc/ssh')),
        Action(type_=ActionType.CHMOD, args=('/USERSPACE/etc/ssh/ssh_key_B', 0o640)),
        Action(type_=ActionType.CHOWN, args=('/USERSPACE/etc/ssh/ssh_key_B', 0, 1)),
        Action(type_=ActionType.COPY, args=('/etc/ssh/ssh_key_A.pub', '/USERSPACE/etc/ssh')),
        Action(type_=ActionType.CHMOD, args=('/USERSPACE/etc/ssh/ssh_key_A.pub', 0o644)),
        Action(type_=ActionType.CHOWN, args=('/USERSPACE/etc/ssh/ssh_key_A.pub', 0, 0)),
        Action(type_=ActionType.CHMOD, args=('/USERSPACE/root/.ssh/authorized_keys', 0o600)),
        Action(type_=ActionType.CHMOD, args=('/USERSPACE/root/.ssh', 0o700)),
        Action(type_=ActionType.SYMLINK,
               args=('/usr/lib/systemd/system/sshd.service',
                     '/USERSPACE/etc/systemd/system/multi-user.target.wants/sshd.service')),
    ]

    error = assert_execution_trace_subsumes_other(actual_trace, expected_trace)
    assert not error, error


def test_create_alternative_fstab(monkeypatch):
    """
    Check whether alternative fstab is created soundly.

    Given host's fstab, an alternative userspace fstab that mounts
    everything into a relative root should be created.
    """

    host_fstab = [
        FstabEntry(fs_spec='/A1', fs_file='/A2', fs_vfstype='ext4',
                   fs_mntops='optsA', fs_freq='freqA', fs_passno='passnoA'),
        FstabEntry(fs_spec='/B1', fs_file='/B2', fs_vfstype='xfs',
                   fs_mntops='optsB', fs_freq='freqB', fs_passno='passnoB'),
        FstabEntry(fs_spec='/swap-dev', fs_file='/swap', fs_vfstype='swap',
                   fs_mntops='opts-swap', fs_freq='freq-swap', fs_passno='passno-swap')
    ]

    actual_trace = []
    context_mock = NspawnActionsMock('/USERSPACE', action_log=actual_trace)

    monkeypatch.setattr(modify_userspace_for_livemode_lib, 'SOURCE_ROOT_MOUNT_LOCATION', '/REL')

    modify_userspace_for_livemode_lib.create_fstab_mounting_current_root_elsewhere(context_mock, host_fstab)

    expected_fstab_contents = (
        '/A1 /REL/A2 ext4 optsA freqA passnoA\n'
        '/B1 /REL/B2 xfs optsB freqB passnoB\n'
        '/swap-dev /swap swap opts-swap freq-swap passno-swap\n'
    )

    expected_trace = [
        Action(type_=ActionType.OPEN, args=('/USERSPACE/etc/fstab',)),
        Action(type_=ActionType.WRITE, args=(expected_fstab_contents,)),
    ]

    error = assert_execution_trace_subsumes_other(actual_trace, expected_trace)
    assert not error, error


def test_alternative_root_symlink_creation(monkeypatch):
    actual_trace = []
    context_mock = NspawnActionsMock('/USERSPACE', action_log=actual_trace)

    def symlink_mock(link_target, symlink_location):
        actual_trace.append(Action(type_=ActionType.SYMLINK, args=(link_target, symlink_location)))

    monkeypatch.setattr(os, 'symlink', symlink_mock)
    monkeypatch.setattr(modify_userspace_for_livemode_lib, 'SOURCE_ROOT_MOUNT_LOCATION', '/NEW-ROOT')

    modify_userspace_for_livemode_lib.create_symlink_from_sysroot_to_source_root_mountpoint(context_mock)

    expected_trace = [
        Action(type_=ActionType.SYMLINK, args=('/NEW-ROOT', '/USERSPACE/sysroot')),
    ]

    error = assert_execution_trace_subsumes_other(actual_trace, expected_trace)
    assert not error, error


def test_enable_dbus(monkeypatch):
    """ Test whether dbus-daemon is activated in the userspace. """

    actual_trace = []
    context_mock = NspawnActionsMock('/USERSPACE', action_log=actual_trace)

    def symlink_mock(link_target, symlink_location):
        actual_trace.append(Action(type_=ActionType.SYMLINK, args=(link_target, symlink_location)))

    monkeypatch.setattr(os, 'symlink', symlink_mock)

    modify_userspace_for_livemode_lib.enable_dbus(context_mock)

    expected_trace = [
        Action(type_=ActionType.SYMLINK,
               args=('/usr/lib/systemd/system/dbus-daemon.service',
                     '/USERSPACE/etc/systemd/system/multi-user.target.wants/dbus-daemon.service')),
        Action(type_=ActionType.SYMLINK,
               args=('/usr/lib/systemd/system/dbus-daemon.service',
                     '/USERSPACE/etc/systemd/system/dbus.service')),
        Action(type_=ActionType.SYMLINK,
               args=('/usr/lib/systemd/system/dbus-daemon.service',
                     '/USERSPACE/etc/systemd/system/messagebus.service')),
    ]

    error = assert_execution_trace_subsumes_other(actual_trace, expected_trace)
    assert not error, error


def test_setup_network(monkeypatch):
    """ Test whether the network is being set up correctly. """

    def listdir_mock(path):
        if path == '/etc/sysconfig/network-scripts':
            return ['ifcfg-A', 'ifcfg-B']
        if path == '/etc/NetworkManager/system-connections':
            return ['conn1', 'conn2']
        assert False, 'listing unexpected path'
        return []  # unreachable, but pylint does not know that

    monkeypatch.setattr(os, 'listdir', listdir_mock)

    mocked_actor = CurrentActorMocked(dst_ver='9.4')
    monkeypatch.setattr(api, 'current_actor', mocked_actor)

    actual_trace = []
    context_mock = NspawnActionsMock(base_dir='/USERSPACE', action_log=actual_trace)

    expected_trace = [
        Action(type_=ActionType.COPY,
               args=('/etc/sysconfig/network-scripts/ifcfg-A',
                     '/USERSPACE/etc/sysconfig/network-scripts/ifcfg-A')),
        Action(type_=ActionType.COPY,
               args=('/etc/sysconfig/network-scripts/ifcfg-B',
                     '/USERSPACE/etc/sysconfig/network-scripts/ifcfg-B')),
        Action(type_=ActionType.COPY,
               args=('/etc/NetworkManager/system-connections/conn1',
                     '/USERSPACE/etc/NetworkManager/system-connections/conn1')),
        Action(type_=ActionType.COPY,
               args=('/etc/NetworkManager/system-connections/conn2',
                     '/USERSPACE/etc/NetworkManager/system-connections/conn2')),
    ]

    modify_userspace_for_livemode_lib.setup_network(context_mock)

    error = assert_execution_trace_subsumes_other(actual_trace, expected_trace)
    assert not error, error


@pytest.mark.parametrize(
    'livemode_config',
    (
        _LiveModeConfig(is_enabled=True, setup_passwordless_root=True),
        _LiveModeConfig(is_enabled=True, setup_opensshd_with_auth_keys='auth-keys-path'),
        _LiveModeConfig(is_enabled=True, setup_network_manager=True),
        _LiveModeConfig(is_enabled=True),
    )
)
def test_individual_modifications_are_performed_only_when_configured(monkeypatch, livemode_config):
    mocked_actor = CurrentActorMocked(dst_ver='9.4')
    monkeypatch.setattr(api, 'current_actor', mocked_actor)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    mandatory_modifications = {
        'setup_upgrade_service',
        'setup_console',
        'create_fstab_mounting_current_root_elsewhere',
        'create_symlink_from_sysroot_to_source_root_mountpoint',
        'create_etc_issue',
        'enable_dbus',
        'fakerootfs',
    }

    optional_modifications = {
        'setup_network',
        'make_root_account_passwordless',
        'setup_sshd',
    }

    actual_modifications = set()

    def modification_mock(modif_name, *args, **kwargs):
        actual_modifications.add(modif_name)

    for mandatory_modification in mandatory_modifications.union(optional_modifications):
        monkeypatch.setattr(modify_userspace_for_livemode_lib, mandatory_modification,
                            functools.partial(modification_mock, mandatory_modification))

    expected_modifications = set()
    if livemode_config.setup_opensshd_with_auth_keys:
        expected_modifications.add('setup_sshd')
    if livemode_config.setup_passwordless_root:
        expected_modifications.add('make_root_account_passwordless')
    if livemode_config.setup_network_manager:
        expected_modifications.add('setup_network')
    expected_modifications = expected_modifications | mandatory_modifications

    userspace_info = TargetUserSpaceInfo(path='<userspace-path>', scratch='<scratch-path>', mounts='<mounts-dir>')
    storage_info = StorageInfo()

    modify_userspace_for_livemode_lib.modify_userspace_as_configured(userspace_info, storage_info, livemode_config)

    assert actual_modifications == expected_modifications
