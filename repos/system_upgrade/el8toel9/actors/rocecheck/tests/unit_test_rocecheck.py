import pytest

from leapp import reporting
from leapp.libraries.actor import rocecheck
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import KernelCmdline, KernelCmdlineArg, RoceDetected


def _kernel_cmdline(params=None):
    if params is None:
        return KernelCmdline(parameters=[])
    k_params = []
    for item in params:
        try:
            key, value = item.split('=', 1)
        except ValueError:
            key = item
            value = None
        k_params.append(KernelCmdlineArg(key=key, value=value))
    return KernelCmdline(parameters=k_params)


def _roce(connected, connecting):
    return RoceDetected(
        roce_nics_connected=connected,
        roce_nics_connecting=connecting
    )


@pytest.mark.parametrize('msgs', (
    [_kernel_cmdline()],
    [_kernel_cmdline(), _roce([], [])],
    [_kernel_cmdline(['net.naming-scheme=rhel-8.7']), _roce([], [])],
))
def test_no_roce(monkeypatch, msgs):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_S390X, msgs=msgs))
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    rocecheck.process()
    assert not reporting.create_report.called


@pytest.mark.parametrize('arch', (
    architecture.ARCH_ARM64,
    architecture.ARCH_X86_64,
    architecture.ARCH_PPC64LE
))
def test_roce_noibmz(monkeypatch, arch):
    def mocked_do_not_call_me(dummy):
        assert False, 'Unexpected call on non-IBMz arch (actor should not do anything).'

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=arch))
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(rocecheck, '_report_old_version', mocked_do_not_call_me)
    monkeypatch.setattr(rocecheck, '_report_wrong_setup', mocked_do_not_call_me)
    monkeypatch.setattr(rocecheck, 'is_kernel_arg_set', mocked_do_not_call_me)
    monkeypatch.setattr(rocecheck.api, 'consume', mocked_do_not_call_me)
    rocecheck.process()


@pytest.mark.parametrize('msgs', (
    [_kernel_cmdline(['net.naming-scheme=rhel-8.7']), _roce(['eno'], [])],
    [_kernel_cmdline(['net.naming-scheme=rhel-8.7']), _roce([], ['eno'])],
    [_kernel_cmdline(['net.naming-scheme=rhel-8.7']), _roce(['enp0', 'enp1'], ['eno'])],
    [_kernel_cmdline(['good', 'net.naming-scheme=rhel-8.7']), _roce(['eno'], [])],
    [_kernel_cmdline(['net.naming-scheme=rhel-8.7', 'good']), _roce(['eno'], [])],
    [_kernel_cmdline(['foo=bar', 'net.naming-scheme=rhel-8.7', 'foo=bar']), _roce(['eno'], [])],
))
@pytest.mark.parametrize('version', ['8.7', '8.8', '8.10'])
def test_roce_ok(monkeypatch, msgs, version):
    curr_actor_mocked = CurrentActorMocked(arch=architecture.ARCH_S390X, src_ver=version, msgs=msgs)
    monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    rocecheck.process()
    assert not reporting.create_report.called


@pytest.mark.parametrize('msgs', (
    [_kernel_cmdline(['net.naming-scheme=rhel-8.7']), _roce(['eno'], [])],
    [_kernel_cmdline(['net.naming-scheme=rhel-8.7']), _roce([], ['eno'])],
    [_kernel_cmdline(['net.naming-scheme=rhel-8.6']), _roce(['eno'], [])],
    [_kernel_cmdline(['net.naming-scheme=rhel-8.6']), _roce(['eno', 'eno1'], ['enp'])],
    [_kernel_cmdline(['foo=bar']), _roce(['eno'], [])],
    [_kernel_cmdline(), _roce(['eno'], [])],
))
@pytest.mark.parametrize('version', ['8.0', '8.3', '8.6'])
def test_roce_old_rhel(monkeypatch, msgs, version):
    curr_actor_mocked = CurrentActorMocked(arch=architecture.ARCH_S390X, src_ver=version, msgs=msgs)
    monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    rocecheck.process()
    assert reporting.create_report.called
    assert any(['version of RHEL' in report['title'] for report in reporting.create_report.reports])


# NOTE: what about the situation when net.naming-scheme is configured multiple times???
@pytest.mark.parametrize('msgs', (
    [_kernel_cmdline(['net.naming-scheme=rhel-8.6']), _roce(['eno'], [])],
    [_kernel_cmdline(['net.naming-scheme=rhel-8.8']), _roce([], ['eno'])],
    [_kernel_cmdline(['foo=bar', 'net.naming-scheme=rhel-8.8']), _roce([], ['eno'])],
    [_kernel_cmdline(['foo=bar', 'net.naming-scheme=rhel-8.8', 'foo=bar']), _roce([], ['eno'])],
    [_kernel_cmdline(['net.naming-scheme']), _roce(['eno'], [])],
    [_kernel_cmdline(['foo=bar']), _roce(['eno'], [])],
    [_kernel_cmdline(['foo=bar', 'bar=foo']), _roce(['eno'], [])],
    [_kernel_cmdline(['rhel-8.7']), _roce([], ['eno'])],
    [_kernel_cmdline(), _roce(['eno'], [])],
))
@pytest.mark.parametrize('version', ['8.6', '8.8'])
def test_roce_wrong_configuration(monkeypatch, msgs, version):
    curr_actor_mocked = CurrentActorMocked(arch=architecture.ARCH_S390X, src_ver=version, msgs=msgs)
    monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    rocecheck.process()
    assert reporting.create_report.called
    assert any(['RoCE configuration' in report['title'] for report in reporting.create_report.reports])
