import pytest

from leapp.libraries.common.config import version
from leapp.models import KernelCmdline, KernelCmdlineArg, Report
from leapp.snactor.fixture import current_actor_context

ballast1 = [KernelCmdlineArg(key=k, value=v) for k, v in [
    ('BOOT_IMAGE', '/vmlinuz-3.10.0-1127.el7.x86_64'),
    ('root', '/dev/mapper/rhel_ibm--p8--kvm--03--guest--02-root'),
    ('ro', ''),
    ('console', 'tty0'),
    ('console', 'ttyS0,115200'),
    ('rd_NO_PLYMOUTH', '')]]
ballast2 = [KernelCmdlineArg(key=k, value=v) for k, v in [
    ('crashkernel', 'auto'),
    ('rd.lvm.lv', 'rhel_ibm-p8-kvm-03-guest-02/root'),
    ('rd.lvm.lv', 'rhel_ibm-p8-kvm-03-guest-02/swap'),
    ('rhgb', ''),
    ('quiet', ''),
    ('LANG', 'en_US.UTF-8')]]


@pytest.mark.parametrize('src_v,parameters,expected_report', [
    ("8.7", [], False),
    ("8.7", [KernelCmdlineArg(key='fips', value='')], False),
    ("8.7", [KernelCmdlineArg(key='fips', value='0')], False),
    ("8.7", [KernelCmdlineArg(key='fips', value='1')], True),
    ("8.7", [KernelCmdlineArg(key='fips', value='11')], False),
    ("8.7", [KernelCmdlineArg(key='fips', value='yes')], False),
    ("8.8", [KernelCmdlineArg(key='fips', value='')], False),
    ("8.8", [KernelCmdlineArg(key='fips', value='0')], False),
    ("8.8", [KernelCmdlineArg(key='fips', value='1')], False),
    ("8.8", [KernelCmdlineArg(key='fips', value='11')], False),
    ("8.8", [KernelCmdlineArg(key='fips', value='yes')], False)
])
def test_check_fips(monkeypatch, current_actor_context, src_v, parameters, expected_report):
    cmdline = KernelCmdline(parameters=ballast1+parameters+ballast2)
    monkeypatch.setattr(version, 'get_source_version', lambda: src_v)
    current_actor_context.feed(cmdline)
    current_actor_context.run()
    if expected_report:
        assert current_actor_context.consume(Report)
    else:
        assert not current_actor_context.consume(Report)
