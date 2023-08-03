import os.path
from collections import namedtuple

import pytest

from leapp.libraries import stdlib
from leapp.libraries.actor import forcedefaultboot
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledTargetKernelInfo

Expected = namedtuple(
    'Expected', (
     'grubby_setdefault',
     'zipl_called'
    )
)

Case = namedtuple(
    'Case',
    ('kernel_exists',
     'entry_default',
     'entry_exists',
     'message_available',
     'arch_s390x'
     )
)

TARGET_KERNEL_NEVRA = 'kernel-core-1.2.3.4.el8.x86_64'
TARGET_KERNEL_VERSION = '1.2.3.4.el8.x86_64'
TARGET_KERNEL_TITLE = 'Red Hat Enterprise Linux ({}) 8.1 (Ootpa)'.format(TARGET_KERNEL_VERSION)
TARGET_KERNEL_PATH = '/boot/vmlinuz-{}'.format(TARGET_KERNEL_VERSION)
TARGET_INITRD_PATH = '/boot/initramfs-{}.img'.format(TARGET_KERNEL_VERSION)

OLD_KERNEL_VERSION = '0.1.2.3.el7.x86_64'
OLD_KERNEL_TITLE = 'Red Hat Enterprise Linux ({}) 7.6 (Maipo)'.format(OLD_KERNEL_VERSION)
OLD_KERNEL_PATH = '/boot/vmlinuz-{}'.format(OLD_KERNEL_VERSION)


CASES = (
    (Case(kernel_exists=True, entry_default=True, entry_exists=True, message_available=True, arch_s390x=False),
     Expected(grubby_setdefault=False, zipl_called=False)),
    (Case(kernel_exists=False, entry_default=False, entry_exists=True, message_available=True, arch_s390x=False),
     Expected(grubby_setdefault=False, zipl_called=False)),
    (Case(kernel_exists=True, entry_default=False, entry_exists=True, message_available=False, arch_s390x=False),
     Expected(grubby_setdefault=False, zipl_called=False)),
    (Case(kernel_exists=True, entry_default=False, entry_exists=False, message_available=False, arch_s390x=False),
     Expected(grubby_setdefault=False, zipl_called=False)),
    (Case(kernel_exists=True, entry_default=False, entry_exists=True, message_available=True, arch_s390x=False),
     Expected(grubby_setdefault=True, zipl_called=False)),
    (Case(kernel_exists=True, entry_default=True, entry_exists=True, message_available=True, arch_s390x=True),
     Expected(grubby_setdefault=False, zipl_called=False)),
    (Case(kernel_exists=False, entry_default=False, entry_exists=True, message_available=True, arch_s390x=True),
     Expected(grubby_setdefault=False, zipl_called=False)),
    (Case(kernel_exists=True, entry_default=False, entry_exists=True, message_available=False, arch_s390x=True),
     Expected(grubby_setdefault=False, zipl_called=False)),
    (Case(kernel_exists=True, entry_default=False, entry_exists=False, message_available=False, arch_s390x=True),
     Expected(grubby_setdefault=False, zipl_called=False)),
    (Case(kernel_exists=True, entry_default=False, entry_exists=True, message_available=True, arch_s390x=True),
     Expected(grubby_setdefault=True, zipl_called=True))
)

_GRUBBY_INFO_TEMPLATE = '''index={entry_index}
kernel=/boot/vmlinuz-{kernel_version}
args="ro rd.lvm.lv=testing/root rd.lvm.lv=testing/swap rhgb quiet LANG=en_US.UTF-8"
root=/dev/mapper/testing-root
initrd=/boot/initramfs-{kernel_version}.img
'''


class MockedRun(object):
    def __init__(self, case):
        self.case = case
        self.called_setdefault = False
        self.called_zipl = False

    def __call__(self, cmd, *args, **kwargs):
        if cmd and cmd[0] == 'grubby':
            target = getattr(self, 'grubby_{}'.format(cmd[1].strip('--').replace('-', '_')), None)
            assert target and 'Unsupport grubby command called'  # pylint: disable=simplifiable-condition
            return target(cmd)  # pylint: disable=not-callable
        if cmd and cmd[0] == '/usr/sbin/zipl':
            self.called_zipl = True
        return None

    def grubby_info(self, cmd):
        assert len(cmd) == 3
        if not self.case.entry_exists:
            raise stdlib.CalledProcessError('A leapp command failed', cmd, {})

        return {
            'stdout': _GRUBBY_INFO_TEMPLATE.format(
                entry_index=0 if self.case.entry_default else 1,
                kernel_version=TARGET_KERNEL_VERSION)
            }

    def grubby_default_kernel(self, cmd):
        assert len(cmd) == 2
        if self.case.entry_default:
            return {'stdout': '{}\n'.format(TARGET_KERNEL_PATH)}
        return {'stdout': '{}\n'.format(OLD_KERNEL_PATH)}

    def grubby_default_index(self, cmd):
        assert len(cmd) == 2
        if self.case.entry_default:
            return {'stdout': '1\n'}
        return {'stdout': '0\n'}

    def grubby_default_title(self, cmd):
        assert len(cmd) == 2
        if self.case.entry_default:
            return {'stdout': '{}\n'.format(TARGET_KERNEL_TITLE)}
        return {'stdout': '{}\n'.format(OLD_KERNEL_TITLE)}

    def grubby_set_default(self, cmd):
        assert len(cmd) == 3
        assert cmd[2] == TARGET_KERNEL_PATH
        self.called_setdefault = True


def mocked_consume(case):
    def impl(*args):
        if case.message_available:
            kernel_img_path = TARGET_KERNEL_PATH if case.kernel_exists else ''
            msg = InstalledTargetKernelInfo(pkg_nevra=TARGET_KERNEL_NEVRA,
                                            kernel_img_path=kernel_img_path,
                                            uname_r='',
                                            initramfs_path=TARGET_INITRD_PATH)
            return iter((msg,))
        return iter(())
    return impl


def mocked_exists(case, orig_path_exists):
    def impl(path):
        if path == TARGET_KERNEL_PATH:
            return case.kernel_exists
        if path == TARGET_INITRD_PATH:
            return case.initrd_exists
        return orig_path_exists(path)
    return impl


@pytest.mark.parametrize('case_result', CASES)
def test_force_default_boot_target_scenario(case_result, monkeypatch):
    case, result = case_result
    arch = architecture.ARCH_S390X if case.arch_s390x else architecture.ARCH_X86_64
    mocked_run = MockedRun(case)
    monkeypatch.setattr(api, 'consume', mocked_consume(case))
    monkeypatch.setattr(stdlib, 'run', mocked_run)
    monkeypatch.setattr(os.path, 'exists', mocked_exists(case, os.path.exists))
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=arch))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    forcedefaultboot.process()
    assert result.grubby_setdefault == mocked_run.called_setdefault
    assert result.zipl_called == mocked_run.called_zipl
