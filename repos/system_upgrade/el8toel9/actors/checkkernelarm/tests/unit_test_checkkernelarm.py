import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import checkkernelarm
from leapp.libraries.common.config.architecture import ARCH_ARM64, ARCH_X86_64
from leapp.libraries.common.kernel import KernelPageSize, KernelType
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import KernelInfo, RPM, RpmTransactionTasks

_KERNEL_PKG = RPM(name='kernel-core', arch='aarch64', version='4.18.0', release='1.el8',
                  epoch='0', packager='', pgpsig='SIG')


def _make_kernel_info(kernel_type=KernelType.ORDINARY, page_size=KernelPageSize.PAGE_SIZE_64K):
    return KernelInfo(
        pkg=_KERNEL_PKG, type=kernel_type, page_size=page_size, uname_r='4.18.0-1.el8.aarch64'
    )


def test_skip_non_arm_architecture(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=ARCH_X86_64))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkkernelarm.process()

    assert not api.produce.called


def test_raises_when_no_kernel_info(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=ARCH_ARM64))

    with pytest.raises(StopActorExecutionError, match='Could not retrieve KernelInfo'):
        checkkernelarm.process()


@pytest.mark.parametrize(
    ('kernel_type', 'page_size', 'expected_pkgs'),
    [
        (
            KernelType.ORDINARY,
            KernelPageSize.PAGE_SIZE_64K,
            ['kernel-64k', 'kernel-64k-core', 'kernel-64k-modules'],
        ),
        (
            KernelType.ORDINARY,
            KernelPageSize.PAGE_SIZE_4K,
            ['kernel', 'kernel-core', 'kernel-modules'],
        ),
        (
            KernelType.REALTIME,
            KernelPageSize.PAGE_SIZE_64K,
            ['kernel-rt-64k', 'kernel-rt-64k-core', 'kernel-rt-64k-modules'],
        ),
        (
            KernelType.REALTIME,
            KernelPageSize.PAGE_SIZE_4K,
            ['kernel-rt', 'kernel-rt-core', 'kernel-rt-modules'],
        ),
    ]
)
def test_produces_rpm_transaction_tasks(monkeypatch, kernel_type, page_size, expected_pkgs):
    kernel_info = _make_kernel_info(kernel_type=kernel_type, page_size=page_size)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=ARCH_ARM64, msgs=[kernel_info]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkkernelarm.process()

    assert api.produce.called == 1
    produced = api.produce.model_instances[0]
    assert isinstance(produced, RpmTransactionTasks)
    assert sorted(produced.to_install) == sorted(expected_pkgs)
