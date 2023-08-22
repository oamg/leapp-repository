import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries import stdlib
from leapp.libraries.actor import scankernel
from leapp.libraries.common import kernel as kernel_lib
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledTargetKernelInfo, InstalledTargetKernelVersion, KernelInfo, RPM
from leapp.utils.deprecation import suppress_deprecation

TARGET_KERNEL_NEVRA = 'kernel-core-1.2.3-4.el9.x86_64'
TARGET_RT_KERNEL_NEVRA = 'kernel-rt-core-1.2.3-4.rt56.7.el9.x86_64'
OLD_KERNEL_NEVRA = 'kernel-core-0.1.2-3.el8.x86_64'
OLD_RT_KERNEL_NEVRA = 'kernel-rt-core-0.1.2-3.rt4.5.el8.x86_64'


class MockedRun(object):

    def __init__(self, stdouts):
        # stdouts should be dict of list of strings: { str: [str1,str2,...]}
        self._stdouts = stdouts

    def __call__(self, *args, **kwargs):
        for key in ('kernel-core', 'kernel-rt-core'):
            if key in args[0]:
                return {'stdout': self._stdouts.get(key, [])}
        return {'stdout': []}


@suppress_deprecation(InstalledTargetKernelVersion)
def assert_produced_messages_are_correct(produced_messages, expected_target_nevra, initramfs_path, kernel_img_path):
    target_evra = expected_target_nevra.replace('kernel-core-', '').replace('kernel-rt-core-', '')
    installed_kernel_ver = [msg for msg in produced_messages if isinstance(msg, InstalledTargetKernelVersion)]
    assert len(installed_kernel_ver) == 1, 'Actor should produce InstalledTargetKernelVersion (backwards compat.)'
    assert installed_kernel_ver[0].version == target_evra

    installed_kernel_info = [msg for msg in produced_messages if isinstance(msg, InstalledTargetKernelInfo)]
    assert len(installed_kernel_info) == 1
    assert installed_kernel_info[0].pkg_nevra == expected_target_nevra

    assert installed_kernel_info[0].initramfs_path == initramfs_path
    assert installed_kernel_info[0].kernel_img_path == kernel_img_path


@pytest.mark.parametrize(
    ('is_rt', 'expected_target_nevra', 'stdouts'),
    [
        (False, TARGET_KERNEL_NEVRA, {'kernel-core': [OLD_KERNEL_NEVRA, TARGET_KERNEL_NEVRA]}),
        (False, TARGET_KERNEL_NEVRA, {'kernel-core': [TARGET_KERNEL_NEVRA, OLD_KERNEL_NEVRA]}),
        (False, TARGET_KERNEL_NEVRA, {
            'kernel-core': [TARGET_KERNEL_NEVRA, OLD_KERNEL_NEVRA],
            'kernel-rt-core': [TARGET_RT_KERNEL_NEVRA, OLD_RT_KERNEL_NEVRA],
        }),
        (True, TARGET_RT_KERNEL_NEVRA, {
            'kernel-rt-core': [OLD_RT_KERNEL_NEVRA, TARGET_RT_KERNEL_NEVRA]
        }),
        (True, TARGET_RT_KERNEL_NEVRA, {
            'kernel-rt-core': [TARGET_RT_KERNEL_NEVRA, OLD_RT_KERNEL_NEVRA]
        }),
        (True, TARGET_RT_KERNEL_NEVRA, {
            'kernel-core': [TARGET_KERNEL_NEVRA, OLD_KERNEL_NEVRA],
            'kernel-rt-core': [TARGET_RT_KERNEL_NEVRA, OLD_RT_KERNEL_NEVRA],
        }),
    ]
)
def test_scaninstalledkernel(monkeypatch, is_rt, expected_target_nevra, stdouts):
    src_kernel_pkg = RPM(name='kernel-core', arch='x86_64', version='0.1.2', release='3',
                         epoch='0', packager='', pgpsig='SOME_OTHER_SIG_X')
    src_kernel_type = kernel_lib.KernelType.REALTIME if is_rt else kernel_lib.KernelType.ORDINARY
    src_kernel_info = KernelInfo(pkg=src_kernel_pkg, type=src_kernel_type, uname_r='X')

    def patched_get_boot_files(nevra):
        assert nevra == expected_target_nevra
        return scankernel.KernelBootFiles(vmlinuz_path='/boot/vmlinuz-X', initramfs_path='/boot/initramfs-X')

    result = []
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='9.0', msgs=[src_kernel_info]))
    monkeypatch.setattr(api, 'produce', result.append)
    monkeypatch.setattr(scankernel, 'run', MockedRun(stdouts))
    monkeypatch.setattr(scankernel, 'get_boot_files_provided_by_kernel_pkg', patched_get_boot_files)
    monkeypatch.setattr(kernel_lib, 'get_uname_r_provided_by_kernel_pkg', lambda nevra: 'uname-r')

    scankernel.process()

    assert_produced_messages_are_correct(result, expected_target_nevra, '/boot/initramfs-X', '/boot/vmlinuz-X')


@pytest.mark.parametrize(
    ('vmlinuz_path', 'initramfs_path', 'extra_kernel_rpm_files'),
    (
        ('/boot/vmlinuz-x', '/boot/initramfs-x', []),
        ('/boot/vmlinuz-x', '/boot/initramfs-x', ['/lib/modules/6.4.10-100.fc37.x86_64/vmlinuz']),
        (None, '/boot/initramfs-x', ['/lib/modules/6.4.10-100.fc37.x86_64/vmlinuz']),
        ('/boot/vmlinuz-x', None, ['/lib/modules/6.4.10-100.fc37.x86_64/vmlinuz']),
    )
)
def test_get_boot_files_provided_by_kernel_pkg(monkeypatch, vmlinuz_path, initramfs_path, extra_kernel_rpm_files):
    def mocked_run(cmd, *args, **kwargs):
        assert cmd == ['rpm', '-q', '-l', TARGET_KERNEL_NEVRA]

        output = list(extra_kernel_rpm_files)
        if vmlinuz_path:
            output.append(vmlinuz_path)
        if initramfs_path:
            output.append(initramfs_path)

        return {
            'stdout': output
        }

    monkeypatch.setattr(scankernel, 'run', mocked_run)

    if not vmlinuz_path or not initramfs_path:
        with pytest.raises(StopActorExecutionError):
            scankernel.get_boot_files_provided_by_kernel_pkg(TARGET_KERNEL_NEVRA)
    else:
        result = scankernel.get_boot_files_provided_by_kernel_pkg(TARGET_KERNEL_NEVRA)
        assert result.vmlinuz_path == vmlinuz_path
        assert result.initramfs_path == initramfs_path


def test_scaninstalledkernel_missing_rt(monkeypatch):
    src_kernel_pkg = RPM(name='kernel-rt-core', arch='x86_64', version='0.1.2', release='3',
                         epoch='0', packager='', pgpsig='SOME_OTHER_SIG_X')
    src_kernel_type = kernel_lib.KernelType.REALTIME
    src_kernel_info = KernelInfo(pkg=src_kernel_pkg, type=src_kernel_type, uname_r='X')

    result = []
    stdouts = {'kernel-core': [TARGET_KERNEL_NEVRA], 'kernel-rt-core': [OLD_RT_KERNEL_NEVRA]}

    def patched_get_boot_content(target_nevra):
        return scankernel.KernelBootFiles(vmlinuz_path='/boot/vmlinuz-X', initramfs_path='/boot/initramfs-X')

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='9.0', msgs=[src_kernel_info]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'produce', result.append)
    monkeypatch.setattr(scankernel, 'run', MockedRun(stdouts))
    monkeypatch.setattr(scankernel, 'get_boot_files_provided_by_kernel_pkg', patched_get_boot_content)
    monkeypatch.setattr(kernel_lib, 'get_uname_r_provided_by_kernel_pkg', lambda nevra: 'uname-r')

    scankernel.process()

    assert api.current_logger.warnmsg

    assert_produced_messages_are_correct(result, TARGET_KERNEL_NEVRA, '/boot/initramfs-X', '/boot/vmlinuz-X')


def test_scaninstalledkernel_missing(monkeypatch):
    src_kernel_pkg = RPM(name='kernel-rt-core', arch='x86_64', version='0.1.2', release='3',
                         epoch='0', packager='', pgpsig='SOME_OTHER_SIG_X')
    src_kernel_type = kernel_lib.KernelType.REALTIME
    src_kernel_info = KernelInfo(pkg=src_kernel_pkg, type=src_kernel_type, uname_r='X')

    result = []

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[src_kernel_info]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'produce', result.append)
    monkeypatch.setattr(scankernel, 'run', MockedRun({}))
    monkeypatch.setattr(kernel_lib, 'get_uname_r_provided_by_kernel_pkg', lambda nevra: 'uname-r')

    scankernel.process()

    assert not result
