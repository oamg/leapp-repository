from collections import namedtuple

import pytest

from leapp.libraries import stdlib
from leapp.libraries.actor import kernelcmdlineconfig
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledTargetKernelInfo, KernelCmdlineArg, TargetKernelCmdlineArgTasks

TARGET_KERNEL_NEVRA = 'kernel-core-1.2.3-4.x86_64.el8.x64_64'


class MockedRun(object):
    def __init__(self):
        self.commands = []

    def __call__(self, cmd, *args, **kwargs):
        self.commands.append(cmd)
        return {}


@pytest.mark.parametrize(
    ('msgs', 'expected_grubby_kernelopt_args'),
    [
        (
            [KernelCmdlineArg(key='key1', value='value1'), KernelCmdlineArg(key='key2', value='value2')],
            ['--args', 'key1=value1 key2=value2']
        ),
        (
            [TargetKernelCmdlineArgTasks(to_add=[KernelCmdlineArg(key='key1', value='value1'),
                                                 KernelCmdlineArg(key='key2')])],
            ['--args', 'key1=value1 key2']
        ),
        (
            [TargetKernelCmdlineArgTasks(to_add=[KernelCmdlineArg(key='key1', value='value1')]),
             KernelCmdlineArg(key='key2', value='value2')],
            ['--args', 'key1=value1 key2=value2']
        ),
        (
            [TargetKernelCmdlineArgTasks(to_add=[KernelCmdlineArg(key='key1', value='value1')],
                                         to_remove=[KernelCmdlineArg(key='key3')]),
             KernelCmdlineArg(key='key2', value='value2')],
            ['--args', 'key1=value1 key2=value2', '--remove-args', 'key3']
        ),
        (
            [TargetKernelCmdlineArgTasks(to_remove=[KernelCmdlineArg(key='key3'), KernelCmdlineArg(key='key4')])],
            ['--remove-args', 'key3 key4']
        ),
    ]
)
def test_kernelcmdline_config_valid_msgs(monkeypatch, msgs, expected_grubby_kernelopt_args):
    kernel_img_path = '/boot/vmlinuz-X'
    kernel_info = InstalledTargetKernelInfo(pkg_nevra=TARGET_KERNEL_NEVRA,
                                            uname_r='',
                                            kernel_img_path=kernel_img_path,
                                            initramfs_path='/boot/initramfs-X')
    msgs += [kernel_info]

    grubby_base_cmd = ['grubby', '--update-kernel={}'.format(kernel_img_path)]
    expected_grubby_cmd = grubby_base_cmd + expected_grubby_kernelopt_args

    mocked_run = MockedRun()
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_X86_64, msgs=msgs))
    kernelcmdlineconfig.modify_kernel_args_in_boot_cfg()
    assert mocked_run.commands and len(mocked_run.commands) == 1
    assert expected_grubby_cmd == mocked_run.commands.pop()

    mocked_run = MockedRun()
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_S390X, msgs=msgs))
    kernelcmdlineconfig.modify_kernel_args_in_boot_cfg()
    assert mocked_run.commands and len(mocked_run.commands) == 2
    assert expected_grubby_cmd == mocked_run.commands.pop(0)
    assert ['/usr/sbin/zipl'] == mocked_run.commands.pop(0)


def test_kernelcmdline_explicit_configs(monkeypatch):
    kernel_img_path = '/boot/vmlinuz-X'

    kernel_info = InstalledTargetKernelInfo(pkg_nevra=TARGET_KERNEL_NEVRA,
                                            uname_r='',
                                            kernel_img_path=kernel_img_path,
                                            initramfs_path='/boot/initramfs-X')
    msgs = [kernel_info, TargetKernelCmdlineArgTasks(to_remove=[KernelCmdlineArg(key='key1', value='value1')])]

    mocked_run = MockedRun()
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_X86_64, msgs=msgs))

    configs = ['/boot/grub2/grub.cfg', '/boot/efi/EFI/redhat/grub.cfg']
    kernelcmdlineconfig.modify_kernel_args_in_boot_cfg(configs_to_modify_explicitly=configs)

    grubby_cmd_without_config = ['grubby', '--update-kernel={}'.format(kernel_img_path),
                                 '--remove-args', 'key1=value1']
    expected_cmds = [
        grubby_cmd_without_config + ['-c', '/boot/grub2/grub.cfg'],
        grubby_cmd_without_config + ['-c', '/boot/efi/EFI/redhat/grub.cfg']
    ]

    assert mocked_run.commands == expected_cmds


def test_kernelcmdline_config_no_args(monkeypatch):
    kernel_info = InstalledTargetKernelInfo(pkg_nevra=TARGET_KERNEL_NEVRA,
                                            uname_r='',
                                            kernel_img_path='/boot/vmlinuz-X',
                                            initramfs_path='/boot/initramfs-X')

    mocked_run = MockedRun()
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_S390X, msgs=[kernel_info]))
    kernelcmdlineconfig.modify_kernel_args_in_boot_cfg()
    assert not mocked_run.commands


def test_kernelcmdline_config_no_version(monkeypatch):
    mocked_run = MockedRun()
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_S390X))
    kernelcmdlineconfig.modify_kernel_args_in_boot_cfg()
    assert not mocked_run.commands
