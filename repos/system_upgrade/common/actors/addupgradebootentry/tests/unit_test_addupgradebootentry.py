import os
from collections import namedtuple

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import addupgradebootentry
from leapp.libraries.common.config.architecture import ARCH_S390X, ARCH_X86_64
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import BootContent, KernelCmdlineArg, TargetKernelCmdlineArgTasks

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


class run_mocked(object):
    def __init__(self):
        self.args = []

    def __call__(self, args, split=False):
        self.args.append(args)


class write_to_file_mocked(object):
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
    'debug enforcing=0 rd.plymouth=0 plymouth.enable=0'
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
    monkeypatch.setenv('LEAPP_DEBUG', '1')
    monkeypatch.setattr(addupgradebootentry, 'run', run_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch))

    addupgradebootentry.add_boot_entry()

    assert len(addupgradebootentry.run.args) == run_args.args_len
    assert addupgradebootentry.run.args[0] == run_args.args_remove
    assert addupgradebootentry.run.args[1] == run_args.args_add
    assert api.produce.model_instances == [
        TargetKernelCmdlineArgTasks(to_remove=[KernelCmdlineArg(key='debug')]),
        TargetKernelCmdlineArgTasks(to_remove=[KernelCmdlineArg(key='enforcing', value='0')])
    ]

    if run_args.args_zipl:
        assert addupgradebootentry.run.args[2] == run_args.args_zipl


@pytest.mark.parametrize('is_leapp_invoked_with_debug', [True, False])
def test_debug_kernelopt_removal_task_production(monkeypatch, is_leapp_invoked_with_debug):
    def get_boot_file_paths_mocked():
        return '/abc', '/def'

    monkeypatch.setattr(addupgradebootentry, 'get_boot_file_paths', get_boot_file_paths_mocked)
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setenv('LEAPP_DEBUG', '1' if is_leapp_invoked_with_debug else '0')
    monkeypatch.setattr(addupgradebootentry, 'run', run_mocked())

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    addupgradebootentry.add_boot_entry()

    expected_produced_messages = []
    if is_leapp_invoked_with_debug:
        expected_produced_messages = [TargetKernelCmdlineArgTasks(to_remove=[KernelCmdlineArg(key='debug')])]

    expected_produced_messages.append(
        TargetKernelCmdlineArgTasks(to_remove=[KernelCmdlineArg(key='enforcing', value='0')])
    )

    assert api.produce.model_instances == expected_produced_messages


def test_add_boot_entry_configs(monkeypatch):
    def get_boot_file_paths_mocked():
        return '/abc', '/def'

    monkeypatch.setattr(addupgradebootentry, 'get_boot_file_paths', get_boot_file_paths_mocked)
    monkeypatch.setenv('LEAPP_DEBUG', '1')
    monkeypatch.setattr(addupgradebootentry, 'run', run_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())

    addupgradebootentry.add_boot_entry(CONFIGS)

    assert len(addupgradebootentry.run.args) == 4
    assert addupgradebootentry.run.args[0] == run_args_remove + ['-c', CONFIGS[0]]
    assert addupgradebootentry.run.args[1] == run_args_remove + ['-c', CONFIGS[1]]
    assert addupgradebootentry.run.args[2] == run_args_add + ['-c', CONFIGS[0]]
    assert addupgradebootentry.run.args[3] == run_args_add + ['-c', CONFIGS[1]]
    assert api.produce.model_instances == [
        TargetKernelCmdlineArgTasks(to_remove=[KernelCmdlineArg(key='debug')]),
        TargetKernelCmdlineArgTasks(to_remove=[KernelCmdlineArg(key='enforcing', value='0')])
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
