from __future__ import division

from collections import namedtuple

import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries import stdlib
from leapp.libraries.actor import kernelcmdlineconfig
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledTargetKernelInfo, KernelCmdlineArg, TargetKernelCmdlineArgTasks

TARGET_KERNEL_NEVRA = 'kernel-core-1.2.3-4.x86_64.el8.x64_64'

# pylint: disable=E501
SAMPLE_KERNEL_ARGS = ('ro rootflags=subvol=root'
                      ' resume=/dev/mapper/luks-2c0df999-81ec-4a35-a1f9-b93afee8c6ad'
                      ' rd.luks.uuid=luks-90a6412f-c588-46ca-9118-5aca35943d25'
                      ' rd.luks.uuid=luks-2c0df999-81ec-4a35-a1f9-b93afee8c6ad rhgb quiet'
                      )
SAMPLE_KERNEL_ROOT = 'UUID=1aa15850-2685-418d-95a6-f7266a2de83a'
TEMPLATE_GRUBBY_INFO_OUTPUT = """index=0
kernel="/boot/vmlinuz-6.5.13-100.fc37.x86_64"
args="{0}"
root="{1}"
initrd="/boot/initramfs-6.5.13-100.fc37.x86_64.img"
title="Fedora Linux (6.5.13-100.fc37.x86_64) 37 (Thirty Seven)"
id="a3018267cdd8451db7c77bb3e5b1403d-6.5.13-100.fc37.x86_64"
"""  # noqa: E501
SAMPLE_GRUBBY_INFO_OUTPUT = TEMPLATE_GRUBBY_INFO_OUTPUT.format(SAMPLE_KERNEL_ARGS, SAMPLE_KERNEL_ROOT)
# pylint: enable=E501


class MockedRun(object):
    def __init__(self, outputs=None):
        """
        Mock stdlib.run().

        If outputs is given, it is a dictionary mapping a cmd to output as stdout.
        """
        self.commands = []
        self.outputs = outputs or {}

    def __call__(self, cmd, *args, **kwargs):
        self.commands.append(cmd)
        return {
            "stdout": self.outputs.get(" ".join(cmd), ""),
            "stderr": "",
            "signal": None,
            "exit_code": 0,
            "pid": 1234,
        }


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
def test_kernelcmdline_config_valid_msgs(monkeypatch, tmpdir, msgs, expected_grubby_kernelopt_args):
    kernel_img_path = '/boot/vmlinuz-X'
    kernel_info = InstalledTargetKernelInfo(pkg_nevra=TARGET_KERNEL_NEVRA,
                                            uname_r='',
                                            kernel_img_path=kernel_img_path,
                                            initramfs_path='/boot/initramfs-X')
    msgs += [kernel_info]

    grubby_base_cmd = ['grubby', '--update-kernel={}'.format(kernel_img_path)]
    expected_grubby_cmd = grubby_base_cmd + expected_grubby_kernelopt_args

    mocked_run = MockedRun(
        outputs={" ".join(("grubby", "--info", kernel_img_path)): SAMPLE_GRUBBY_INFO_OUTPUT}
    )
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(architecture.ARCH_X86_64,
                                           dst_ver="8.1",
                                           msgs=msgs)
                        )
    kernelcmdlineconfig.modify_kernel_args_in_boot_cfg()
    assert mocked_run.commands and len(mocked_run.commands) == 3
    assert expected_grubby_cmd == mocked_run.commands.pop(0)

    mocked_run = MockedRun(
        outputs={" ".join(("grubby", "--info", kernel_img_path)): SAMPLE_GRUBBY_INFO_OUTPUT}
    )
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_S390X, msgs=msgs))
    monkeypatch.setattr(kernelcmdlineconfig, 'KERNEL_CMDLINE_FILE', str(tmpdir / 'cmdline'))

    kernelcmdlineconfig.modify_kernel_args_in_boot_cfg()
    assert mocked_run.commands and len(mocked_run.commands) == 3
    assert expected_grubby_cmd == mocked_run.commands.pop(0)
    assert ['/usr/sbin/zipl'] == mocked_run.commands.pop(0)


def test_kernelcmdline_explicit_configs(monkeypatch):
    kernel_img_path = '/boot/vmlinuz-X'

    kernel_info = InstalledTargetKernelInfo(pkg_nevra=TARGET_KERNEL_NEVRA,
                                            uname_r='',
                                            kernel_img_path=kernel_img_path,
                                            initramfs_path='/boot/initramfs-X')
    msgs = [kernel_info, TargetKernelCmdlineArgTasks(to_remove=[KernelCmdlineArg(key='key1', value='value1')])]

    grubby_cmd_info = ["grubby", "--info", kernel_img_path]
    mocked_run = MockedRun(
        outputs={" ".join(grubby_cmd_info): SAMPLE_GRUBBY_INFO_OUTPUT}
    )
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(architecture.ARCH_X86_64,
                                           dst_ver="8.1",
                                           msgs=msgs
                                           )
                        )

    configs = ['/boot/grub2/grub.cfg', '/boot/efi/EFI/redhat/grub.cfg']
    kernelcmdlineconfig.modify_kernel_args_in_boot_cfg(configs_to_modify_explicitly=configs)

    grubby_cmd_without_config = ['grubby', '--update-kernel={}'.format(kernel_img_path),
                                 '--remove-args', 'key1=value1']
    expected_cmds = [
        grubby_cmd_without_config + ['-c', '/boot/grub2/grub.cfg'],
        grubby_cmd_without_config + ['-c', '/boot/efi/EFI/redhat/grub.cfg'],
        grubby_cmd_info,
        ["grub2-editenv", "-", "set", "kernelopts=root={} {}".format(
            SAMPLE_KERNEL_ROOT, SAMPLE_KERNEL_ARGS)],
    ]

    assert mocked_run.commands == expected_cmds


def test_kernelcmdline_config_no_args(monkeypatch):
    kernel_img_path = '/boot/vmlinuz-X'
    kernel_info = InstalledTargetKernelInfo(pkg_nevra=TARGET_KERNEL_NEVRA,
                                            uname_r='',
                                            kernel_img_path=kernel_img_path,
                                            initramfs_path='/boot/initramfs-X')

    mocked_run = MockedRun(
        outputs={" ".join(("grubby", "--info", kernel_img_path)):
                 TEMPLATE_GRUBBY_INFO_OUTPUT.format("", "")
                 }
    )
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


SECOND_KERNEL_ARGS = (
    'ro rootflags=subvol=root'
    ' resume=/dev/mapper/luks-2c0df999-81ec-4a35-a1f9-b93afee8c6ad'
    ' rd.luks.uuid=luks-90a6412f-c588-46ca-9118-5aca35943d25'
    ' rd.luks.uuid=luks-2c0df999-81ec-4a35-a1f9-b93afee8c6ad'
)
SECOND_KERNEL_ROOT = 'UUID=1aa15850-2685-418d-95a6-f7266a2de83b'


@pytest.mark.parametrize(
    'second_grubby_output',
    (
        TEMPLATE_GRUBBY_INFO_OUTPUT.format(SECOND_KERNEL_ARGS, SECOND_KERNEL_ROOT),
        TEMPLATE_GRUBBY_INFO_OUTPUT.format(SAMPLE_KERNEL_ARGS, SECOND_KERNEL_ROOT),
        TEMPLATE_GRUBBY_INFO_OUTPUT.format(SECOND_KERNEL_ARGS, SAMPLE_KERNEL_ROOT),
    )
)
def test_kernelcmdline_config_mutiple_args(monkeypatch, second_grubby_output):
    kernel_img_path = '/boot/vmlinuz-X'
    kernel_info = InstalledTargetKernelInfo(pkg_nevra=TARGET_KERNEL_NEVRA,
                                            uname_r='',
                                            kernel_img_path=kernel_img_path,
                                            initramfs_path='/boot/initramfs-X')

    # For this test, we need to check we get the proper report if grubby --info
    # outputs multiple different `root=` or `args=`
    # and that the first ones are used
    grubby_info_output = "\n".join((SAMPLE_GRUBBY_INFO_OUTPUT, second_grubby_output))

    mocked_run = MockedRun(
        outputs={" ".join(("grubby", "--info", kernel_img_path)): grubby_info_output,
                 }
    )
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    root, args = kernelcmdlineconfig.retrieve_args_for_default_kernel(kernel_info)
    assert root == SAMPLE_KERNEL_ROOT
    assert args == SAMPLE_KERNEL_ARGS
    assert reporting.create_report.called == 1
    expected_title = 'Ensure that expected default kernel cmdline arguments are set'
    assert expected_title in reporting.create_report.report_fields['title']


def test_kernelcmdline_config_malformed_args(monkeypatch):
    kernel_img_path = '/boot/vmlinuz-X'
    kernel_info = InstalledTargetKernelInfo(pkg_nevra=TARGET_KERNEL_NEVRA,
                                            uname_r='',
                                            kernel_img_path=kernel_img_path,
                                            initramfs_path='/boot/initramfs-X')

    # For this test, we need to check we get the proper error if grubby --info
    # doesn't output any args information at all.
    grubby_info_output = "\n".join(line for line in SAMPLE_GRUBBY_INFO_OUTPUT.splitlines()
                                   if not line.startswith("args="))
    mocked_run = MockedRun(
        outputs={" ".join(("grubby", "--info", kernel_img_path)): grubby_info_output,
                 }
    )
    msgs = [kernel_info,
            TargetKernelCmdlineArgTasks(to_remove=[
                KernelCmdlineArg(key='key1', value='value1')])
            ]
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(architecture.ARCH_S390X, msgs=msgs))

    with pytest.raises(kernelcmdlineconfig.ReadOfKernelArgsError,
                       match="Failed to retrieve kernel command line to save for future"
                       " installed kernels."):
        kernelcmdlineconfig.modify_kernel_args_in_boot_cfg()
