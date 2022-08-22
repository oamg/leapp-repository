import pytest

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


@pytest.mark.parametrize('parameters,expected_report', [
    ([], False),
    ([KernelCmdlineArg(key='fips', value='')], False),
    ([KernelCmdlineArg(key='fips', value='0')], False),
    ([KernelCmdlineArg(key='fips', value='1')], True),
    ([KernelCmdlineArg(key='fips', value='11')], False),
    ([KernelCmdlineArg(key='fips', value='yes')], False)
])
def test_check_fips(current_actor_context, parameters, expected_report):
    cmdline = KernelCmdline(parameters=ballast1+parameters+ballast2)
    current_actor_context.feed(cmdline)
    current_actor_context.run()
    if expected_report:
        assert current_actor_context.consume(Report)
    else:
        assert not current_actor_context.consume(Report)
