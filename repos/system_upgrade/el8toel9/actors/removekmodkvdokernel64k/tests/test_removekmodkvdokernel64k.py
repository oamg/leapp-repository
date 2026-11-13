import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import removekmodkvdokernel64k
from leapp.libraries.common.config.architecture import ARCH_ARM64, ARCH_X86_64
from leapp.libraries.common.kernel import KernelPageSize, KernelType
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, KernelInfo, RPM, RpmTransactionTasks

_KERNEL_PKG = RPM(
    name='kernel-core', arch='aarch64', version='4.18.0', release='1.el8',
    epoch='0', packager='', pgpsig='SIG'
)


def _rpm(name):
    return RPM(
        name=name, arch='aarch64', version='1', release='1.el8',
        epoch='0', packager='', pgpsig='SIG'
    )


def _make_kernel_info(page_size=KernelPageSize.PAGE_SIZE_64K):
    return KernelInfo(
        pkg=_KERNEL_PKG, type=KernelType.ORDINARY, page_size=page_size,
        uname_r='4.18.0-1.el8.aarch64'
    )


def _prepare(monkeypatch, arch, msgs=None):
    kwargs = {'arch': arch}
    if msgs is not None:
        kwargs['msgs'] = msgs
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(**kwargs))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())


def test_skip_non_arm_architecture(monkeypatch):
    """Actor should do nothing on non-aarch64 architectures."""
    _prepare(monkeypatch, ARCH_X86_64)

    removekmodkvdokernel64k.process()

    assert not api.produce.called
    assert not reporting.create_report.called


def test_skip_kmod_kvdo_not_installed(monkeypatch):
    """Actor should do nothing when kmod-kvdo is not installed."""
    _prepare(monkeypatch, ARCH_ARM64, msgs=[
        DistributionSignedRPM(items=[_rpm('vim-enhanced')]),
        _make_kernel_info(),
    ])

    removekmodkvdokernel64k.process()

    assert not api.produce.called
    assert not reporting.create_report.called


def test_raises_when_no_kernel_info(monkeypatch):
    """Actor should raise StopActorExecutionError when KernelInfo is not available."""
    _prepare(monkeypatch, ARCH_ARM64, msgs=[
        DistributionSignedRPM(items=[_rpm('kmod-kvdo')]),
    ])

    with pytest.raises(StopActorExecutionError, match='Could not retrieve KernelInfo'):
        removekmodkvdokernel64k.process()

    assert not api.produce.called
    assert not reporting.create_report.called


def test_skip_4k_page_size(monkeypatch):
    """Actor should do nothing when kernel page size is 4k (no kernel-64k conflict)."""
    _prepare(monkeypatch, ARCH_ARM64, msgs=[
        DistributionSignedRPM(items=[_rpm('kmod-kvdo')]),
        _make_kernel_info(page_size=KernelPageSize.PAGE_SIZE_4K),
    ])

    removekmodkvdokernel64k.process()

    assert not api.produce.called
    assert not reporting.create_report.called


def test_remove_kmod_kvdo_on_64k(monkeypatch):
    """Actor should produce to_remove and a report when all conditions are met."""
    _prepare(monkeypatch, ARCH_ARM64, msgs=[
        DistributionSignedRPM(items=[_rpm('kmod-kvdo')]),
        _make_kernel_info(),
    ])

    removekmodkvdokernel64k.process()

    assert api.produce.called == 1
    produced = api.produce.model_instances[0]
    assert isinstance(produced, RpmTransactionTasks)
    assert produced.to_remove == ['kmod-kvdo']

    assert reporting.create_report.called == 1
    report_fields = reporting.create_report.report_fields
    assert report_fields.get('title') == 'kmod-kvdo package will be removed during the upgrade'
    assert report_fields.get('summary', '').startswith(
        'The kmod-kvdo package will be removed during the upgrade because'
    )
    assert report_fields.get('severity') == reporting.Severity.INFO
    assert reporting.Groups.KERNEL in report_fields.get('groups', [])
    assert reporting.Groups.DRIVERS in report_fields.get('groups', [])
