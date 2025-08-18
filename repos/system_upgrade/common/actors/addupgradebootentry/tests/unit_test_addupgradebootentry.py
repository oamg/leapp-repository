import os
import shutil
from collections import namedtuple

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import addupgradebootentry
from leapp.libraries.common.config.architecture import ARCH_S390X, ARCH_X86_64
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    ArmWorkaroundEFIBootloaderInfo,
    BootContent,
    EFIBootEntry,
    KernelCmdline,
    KernelCmdlineArg,
    LateTargetKernelCmdlineArgTasks,
    LiveModeArtifacts,
    LiveModeConfig,
    TargetKernelCmdlineArgTasks
)

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


class run_mocked:
    def __init__(self):
        self.args = []

    def __call__(self, args, split=False):
        self.args.append(args)


class write_to_file_mocked:
    def __init__(self):
        self.content = None

    def __call__(self, filename, content):
        self.content = content


CONFIGS = ['/boot/grub2/grub.cfg', '/boot/efi/EFI/redhat/grub.cfg']

RunArgs = namedtuple('RunArgs', 'args_remove args_add args_zipl args_len')

run_args_remove = [
    '/usr/sbin/grubby',
    '--remove-kernel', '/abc'
]

run_args_add = [
    '/usr/sbin/grubby',
    '--add-kernel', '/abc',
    '--initrd', '/def',
    '--title', 'RHEL-Upgrade-Initramfs',
    '--copy-default',
    '--make-default',
    '--args',
    'debug enforcing=0 plymouth.enable=0 rd.plymouth=0'
    ]

run_args_zipl = ['/usr/sbin/zipl']


@pytest.mark.parametrize('run_args, arch', [
    # non s390x
    (RunArgs(run_args_remove, run_args_add, None, 2), ARCH_X86_64),
    # s390x
    (RunArgs(run_args_remove, run_args_add, run_args_zipl, 3), ARCH_S390X),
    # config file specified
    (RunArgs(run_args_remove, run_args_add, None, 2), ARCH_X86_64),
])
def test_add_boot_entry(monkeypatch, run_args, arch):
    def get_boot_file_paths_mocked():
        return '/abc', '/def'

    monkeypatch.setattr(addupgradebootentry, 'get_boot_file_paths', get_boot_file_paths_mocked)
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(addupgradebootentry, 'run', run_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch, envars={'LEAPP_DEBUG': '1'}))

    addupgradebootentry.add_boot_entry()

    assert len(addupgradebootentry.run.args) == run_args.args_len
    assert addupgradebootentry.run.args[0] == run_args.args_remove
    assert addupgradebootentry.run.args[1] == run_args.args_add
    assert api.produce.model_instances == [
        LateTargetKernelCmdlineArgTasks(to_remove=[KernelCmdlineArg(key='debug'),
                                                   KernelCmdlineArg(key='enforcing', value='0'),
                                                   KernelCmdlineArg(key='plymouth.enable', value='0'),
                                                   KernelCmdlineArg(key='rd.plymouth', value='0')])
    ]

    if run_args.args_zipl:
        assert addupgradebootentry.run.args[2] == run_args.args_zipl


@pytest.mark.parametrize('is_leapp_invoked_with_debug', [True, False])
def test_debug_kernelopt_removal_task_production(monkeypatch, is_leapp_invoked_with_debug):
    def get_boot_file_paths_mocked():
        return '/abc', '/def'

    monkeypatch.setattr(addupgradebootentry, 'get_boot_file_paths', get_boot_file_paths_mocked)
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(addupgradebootentry, 'run', run_mocked())

    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(envars={'LEAPP_DEBUG': str(int(is_leapp_invoked_with_debug))}))

    addupgradebootentry.add_boot_entry()
    assert len(api.produce.model_instances) == 1

    produced_msg = api.produce.model_instances[0]
    assert isinstance(produced_msg, LateTargetKernelCmdlineArgTasks)

    debug_kernel_cmline_arg = KernelCmdlineArg(key='debug')
    if is_leapp_invoked_with_debug:
        assert debug_kernel_cmline_arg in produced_msg.to_remove
    else:
        assert debug_kernel_cmline_arg not in produced_msg.to_remove


def test_add_boot_entry_configs(monkeypatch):
    def get_boot_file_paths_mocked():
        return '/abc', '/def'

    monkeypatch.setattr(addupgradebootentry, 'get_boot_file_paths', get_boot_file_paths_mocked)
    monkeypatch.setattr(addupgradebootentry, 'run', run_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(envars={'LEAPP_DEBUG': '1'}))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    addupgradebootentry.add_boot_entry(CONFIGS)

    assert len(addupgradebootentry.run.args) == 4
    assert addupgradebootentry.run.args[0] == run_args_remove + ['-c', CONFIGS[0]]
    assert addupgradebootentry.run.args[1] == run_args_remove + ['-c', CONFIGS[1]]
    assert addupgradebootentry.run.args[2] == run_args_add + ['-c', CONFIGS[0]]
    assert addupgradebootentry.run.args[3] == run_args_add + ['-c', CONFIGS[1]]
    assert api.produce.model_instances == [
        LateTargetKernelCmdlineArgTasks(to_remove=[KernelCmdlineArg(key='debug'),
                                                   KernelCmdlineArg(key='enforcing', value='0'),
                                                   KernelCmdlineArg(key='plymouth.enable', value='0'),
                                                   KernelCmdlineArg(key='rd.plymouth', value='0')])
    ]


def test_get_boot_file_paths(monkeypatch):
    # BootContent message available
    def consume_message_mocked(*models):
        yield BootContent(kernel_path='/ghi', initram_path='/jkl', kernel_hmac_path='/path')

    monkeypatch.setattr('leapp.libraries.stdlib.api.consume', consume_message_mocked)

    kernel_path, initram_path = addupgradebootentry.get_boot_file_paths()

    assert kernel_path == '/ghi' and initram_path == '/jkl'

    # No BootContent message available
    def consume_no_message_mocked(*models):
        yield None

    monkeypatch.setattr('leapp.libraries.stdlib.api.consume', consume_no_message_mocked)

    with pytest.raises(StopActorExecutionError):
        addupgradebootentry.get_boot_file_paths()


@pytest.mark.parametrize(
    ('error_type', 'test_file_name'),
    [
        ('GRUB_CMDLINE_LINUX syntax', 'grub_test'),
        ('missing newline', 'grub_test_newline')
    ]
)
def test_fix_grub_config_error(monkeypatch, error_type, test_file_name):
    monkeypatch.setattr(addupgradebootentry, 'write_to_file', write_to_file_mocked())
    addupgradebootentry.fix_grub_config_error(os.path.join(CUR_DIR, 'files/{}.wrong'.format(test_file_name)),
                                              error_type)

    with open(os.path.join(CUR_DIR, 'files/{}.fixed'.format(test_file_name))) as f:
        assert addupgradebootentry.write_to_file.content == f.read()


@pytest.mark.parametrize(
    ('is_debug_enabled', 'network_enablement_type'),
    (
        (True, 'network-manager'),
        (True, 'scripts'),
        (True, False),
        (False, False),
    )
)
def test_collect_upgrade_kernel_args(monkeypatch, is_debug_enabled, network_enablement_type):
    env_vars = {'LEAPP_DEBUG': str(int(is_debug_enabled))}
    if network_enablement_type:
        env_vars['LEAPP_DEVEL_INITRAM_NETWORK'] = network_enablement_type

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(envars=env_vars))
    monkeypatch.setattr(addupgradebootentry, 'construct_cmdline_args_for_livemode',
                        lambda *args: {'livemodearg': 'value'})

    arg_set = addupgradebootentry.collect_upgrade_kernel_args(livemode_enabled=True)
    args = dict(arg_set)

    assert args['enforcing'] == '0'
    assert args['rd.plymouth'] == '0'
    assert args['plymouth.enable'] == '0'
    assert args['livemodearg'] == 'value'

    if is_debug_enabled:
        assert args['debug'] is None

    if network_enablement_type:
        assert args['ip'] == 'dhcp'
        assert args['rd.neednet'] == '1'


@pytest.mark.parametrize(
    'livemode_config',
    (
        LiveModeConfig(is_enabled=True,
                       squashfs_fullpath='/dir/squashfs.img',
                       url_to_load_squashfs_from='my-url'),
        LiveModeConfig(is_enabled=True,
                       squashfs_fullpath='/dir/squashfs.img',
                       dracut_network="ip=192.168.122.146::192.168.122.1:255.255.255.0:foo::none"),
        LiveModeConfig(is_enabled=True,
                       squashfs_fullpath='/dir/squashfs.img',
                       autostart_upgrade_after_reboot=False),
        LiveModeConfig(is_enabled=True,
                       squashfs_fullpath='/dir/squashfs.img',
                       autostart_upgrade_after_reboot=True),
        LiveModeConfig(is_enabled=True,
                       squashfs_fullpath='/dir/squashfs.img',
                       capture_upgrade_strace_into='/var/strace.out'),
    ),
)
def test_construct_cmdline_for_livemode(monkeypatch, livemode_config):
    artifacts = LiveModeArtifacts(squashfs_path=livemode_config.squashfs_fullpath)
    messages = [livemode_config, artifacts]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=messages))

    monkeypatch.setattr(addupgradebootentry, '_get_device_uuid', lambda *args: 'MY_UUID')

    args = addupgradebootentry.construct_cmdline_args_for_livemode()

    assert 'rw' in args

    if livemode_config.url_to_load_squashfs_from:
        assert args['root'] == 'live:my-url'
    else:
        assert args['root'] == 'live:UUID=MY_UUID'
        assert args['rd.live.dir'] == '/dir'
        assert args['rd.live.squashimg'] == 'squashfs.img'

    if livemode_config.dracut_network:
        assert args['ip'] == '192.168.122.146::192.168.122.1:255.255.255.0:foo::none'
        assert args['rd.needsnet'] == '1'

    assert args['upgrade.autostart'] == str(int(livemode_config.autostart_upgrade_after_reboot))

    if livemode_config.capture_upgrade_strace_into:
        assert args['upgrade.strace'] == livemode_config.capture_upgrade_strace_into


def test_get_rdlvm_arg_values(monkeypatch):
    cmdline = [
        KernelCmdlineArg(key='debug', value=None),
        KernelCmdlineArg(key='rd.lvm.lv', value='A'),
        KernelCmdlineArg(key='other', value='A'),
        KernelCmdlineArg(key='rd.lvm.lv', value='B')
    ]
    messages = [KernelCmdline(parameters=cmdline)]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=messages))

    args = addupgradebootentry._get_rdlvm_arg_values()

    assert args == ('A', 'B')


def test_get_device_uuid(monkeypatch):
    """
    The file in question is /var/lib/file
    Underlying partition /var is a device /dev/sda1 (dev_id=10) linked to from /dev/disk/by-uuid/MY_UUID1
    """

    execution_stats = {
        'is_mount_call_count': 0
    }

    def is_mount_mock(path):
        execution_stats['is_mount_call_count'] += 1
        assert execution_stats['is_mount_call_count'] <= 3
        return path == '/var'

    monkeypatch.setattr(os.path, 'ismount', is_mount_mock)

    StatResult = namedtuple('StatResult', ('st_dev', 'st_rdev'))

    def stat_mock(path):
        known_paths_table = {
            '/var': StatResult(st_dev=1, st_rdev=None),
            '/dev/sda1': StatResult(st_dev=0, st_rdev=1),
            '/dev/sda2': StatResult(st_dev=0, st_rdev=2),
            '/dev/vda0': StatResult(st_dev=0, st_rdev=3),
        }
        return known_paths_table[path]

    monkeypatch.setattr(addupgradebootentry, 'local_os_stat', stat_mock)

    def listdir_mock(path):
        assert path == '/dev/disk/by-uuid'
        return ['MY_UUID0', 'MY_UUID1', 'MY_UUID2']

    monkeypatch.setattr(os, 'listdir', listdir_mock)

    def readlink_mock(path):
        known_links = {
            '/dev/disk/by-uuid/MY_UUID0': '/dev/vda0',
            '/dev/disk/by-uuid/MY_UUID1': '../../sda1',
            '/dev/disk/by-uuid/MY_UUID2': '../../sda2',
        }
        return known_links[path]

    monkeypatch.setattr(os, 'readlink', readlink_mock)

    path = '/var/lib/file'
    uuid = addupgradebootentry._get_device_uuid(path)

    assert uuid == 'MY_UUID1'


@pytest.mark.parametrize('has_separate_boot', (True, False))
def test_modify_grubenv_to_have_separate_blsdir(monkeypatch, has_separate_boot):
    efi_info = ArmWorkaroundEFIBootloaderInfo(
        original_entry=EFIBootEntry(
            boot_number='0001',
            label='Redhat',
            active=True,
            efi_bin_source="HD(.*)/File(\\EFI\\redhat\\shimx64.efi)",
        ),
        upgrade_entry=EFIBootEntry(
            boot_number='0002',
            label='Leapp',
            active=True,
            efi_bin_source="HD(.*)/File(\\EFI\\leapp\\shimx64.efi)",
        ),
        upgrade_bls_dir='/boot/upgrade-loader/entries',
        upgrade_entry_efi_path='/boot/efi/EFI/leapp'
    )

    def is_mount_mocked(path):
        assert path.rstrip('/') == '/boot'
        return has_separate_boot

    def list_grubenv_variables_mock():
        blsdir = '/blsdir' if has_separate_boot else '/boot/blsdir'
        return {
            'blsdir': blsdir
        }

    def listdir_mock(dir_path):
        assert dir_path == '/boot/blsdir'
        return [
            '4a9c76478b98444fb5e0fbf533950edf-6.12.5-200.fc41.x86_64.conf',
            '4a9c76478b98444fb5e0fbf533950edf-upgrade.aarch64.conf',
        ]

    def assert_path_correct(path):
        assert path == efi_info.upgrade_bls_dir

    def move_mocked(src, dst):
        assert src == '/boot/blsdir/4a9c76478b98444fb5e0fbf533950edf-upgrade.aarch64.conf'
        assert dst == '/boot/upgrade-loader/entries/4a9c76478b98444fb5e0fbf533950edf-upgrade.aarch64.conf'

    def run_mocked(cmd, *arg, **kwargs):
        blsdir = '/upgrade-loader/entries' if has_separate_boot else '/boot/upgrade-loader/entries'
        assert cmd == ['grub2-editenv', '/boot/efi/EFI/leapp/grubenv', 'set', 'blsdir={}'.format(blsdir)]

    monkeypatch.setattr(addupgradebootentry, '_list_grubenv_variables', list_grubenv_variables_mock)
    monkeypatch.setattr(os, 'listdir', listdir_mock)
    monkeypatch.setattr(os.path, 'exists', assert_path_correct)
    monkeypatch.setattr(os.path, 'ismount', is_mount_mocked)
    monkeypatch.setattr(os, 'makedirs', assert_path_correct)
    monkeypatch.setattr(shutil, 'move', move_mocked)
    monkeypatch.setattr(addupgradebootentry, 'run', run_mocked)

    addupgradebootentry.modify_our_grubenv_to_have_separate_blsdir(efi_info)
