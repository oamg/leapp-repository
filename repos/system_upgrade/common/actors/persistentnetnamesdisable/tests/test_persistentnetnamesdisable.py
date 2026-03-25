import pytest

from leapp.libraries.actor import persistentnetnamesdisable
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.models import (
    Interface,
    KernelCmdline,
    KernelCmdlineArg,
    PCIAddress,
    PersistentNetNamesFacts,
    TargetKernelCmdlineArgTasks,
    UpgradeKernelCmdlineArgTasks
)
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context
from leapp.utils.report import is_inhibitor


def _gen_ifaces_by_names(names):
    pci = PCIAddress(domain="0000", bus="3e", function="00", device="PCI bridge")
    interfaces = []
    for nic_name in names:
        interfaces.append(Interface(
            name=nic_name,
            devpath="/devices/platform/usb/cdc-wdm0",
            driver="pcieport",
            mac="52:54:00:0b:4a:6d",
            pci_info=pci,
            vendor="redhat",
        ))
    return interfaces


@pytest.mark.parametrize(('interfaces', 'exp_result'), (
    (_gen_ifaces_by_names(['eno1', 'eno2', 'myfoo00', 'nicname']), 0),
    (_gen_ifaces_by_names(['preeth0', 'eth2post', 'preeth0post']), 0),
    (_gen_ifaces_by_names(['eth0']), 1),
    (_gen_ifaces_by_names(['eth0', 'eth1', 'eth01', 'eth4980']), 4),
    (_gen_ifaces_by_names(['myeth0', 'eth0', 'something']), 1),
))
def test_ethX_count(interfaces, exp_result):
    """
    Test the correct detection of ethX interfaces.

    It tests the bug causing https://issues.redhat.com/browse/RHEL-3370
    """
    assert persistentnetnamesdisable.ethX_count(interfaces) == exp_result


def test_actor_single_eth0(current_actor_context):
    pci = PCIAddress(domain="0000", bus="3e", function="00", device="PCI bridge")
    interface = [Interface(
        name="eth0",
        mac="52:54:00:0b:4a:6d",
        vendor="redhat",
        driver="pcieport",
        pci_info=pci,
        devpath="/devices/platform/usb/cdc-wdm0"
    )]
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interface))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
    assert current_actor_context.consume(UpgradeKernelCmdlineArgTasks)
    assert current_actor_context.consume(TargetKernelCmdlineArgTasks)


@pytest.mark.parametrize(
    'target_version', ['9', '10']
)
def test_actor_more_ethX(monkeypatch, current_actor_context, target_version):
    monkeypatch.setattr(persistentnetnamesdisable, 'get_source_major_version', lambda: str(int(target_version) - 1))
    monkeypatch.setattr(persistentnetnamesdisable, 'get_target_major_version', lambda: target_version)
    pci1 = PCIAddress(domain="0000", bus="3e", function="00", device="PCI bridge")
    pci2 = PCIAddress(domain="0000", bus="3d", function="00", device="Serial controller")
    interface = [
        Interface(
            name="eth0",
            mac="52:54:00:0b:4a:6d",
            vendor="redhat",
            driver="pcieport",
            pci_info=pci1,
            devpath="/devices/platform/usb/cdc-wdm0"),
        Interface(
            name="eth1",
            mac="52:54:00:0b:4a:6a",
            vendor="redhat",
            driver="serial",
            pci_info=pci2,
            devpath="/devices/hidraw/hidraw0")
    ]
    current_actor_context.feed(
        PersistentNetNamesFacts(interfaces=interface),
        KernelCmdline(parameters=[KernelCmdlineArg(key='what', value='ever')])
    )
    current_actor_context.run()

    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)

    external_links = report_fields.get('detail', {}).get('external', [])

    rhel8to9_present = any(
        'RHEL 8 to RHEL 9' in link.get('title', '') for link in external_links
    )

    if target_version == '9':
        assert rhel8to9_present
    else:
        assert not rhel8to9_present


def test_actor_single_int_not_ethX(current_actor_context):
    pci = PCIAddress(domain="0000", bus="3e", function="00", device="PCI bridge")
    interface = [
        Interface(
            name="tap0",
            mac="52:54:00:0b:4a:60",
            vendor="redhat",
            driver="pcieport",
            pci_info=pci,
            devpath="/devices/platform/usb/cdc-wdm0")
    ]
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interface))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


@pytest.mark.parametrize(
    'target_version', ['9', '10']
)
def test_actor_ethX_and_not_ethX(monkeypatch, current_actor_context, target_version):
    monkeypatch.setattr(persistentnetnamesdisable, 'get_source_major_version', lambda: str(int(target_version) - 1))
    monkeypatch.setattr(persistentnetnamesdisable, 'get_target_major_version', lambda: target_version)
    pci1 = PCIAddress(domain="0000", bus="3e", function="00", device="PCI bridge")
    pci2 = PCIAddress(domain="0000", bus="3d", function="00", device="Serial controller")
    interface = [
        Interface(
            name="virbr0",
            mac="52:54:00:0b:4a:6d",
            vendor="redhat",
            driver="pcieport",
            pci_info=pci1,
            devpath="/devices/platform/usb/cdc-wdm0"),
        Interface(
            name="eth0",
            mac="52:54:00:0b:4a:6a",
            vendor="redhat",
            driver="serial",
            pci_info=pci2,
            devpath="/devices/hidraw/hidraw0")
    ]
    current_actor_context.feed(
        PersistentNetNamesFacts(interfaces=interface),
        KernelCmdline(parameters=[KernelCmdlineArg(key='what', value='ever')])
    )
    current_actor_context.run()
    assert current_actor_context.consume(Report)

    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)

    external_links = report_fields.get('detail', {}).get('external', [])

    rhel8to9_present = any(
        'RHEL 8 to RHEL 9' in link.get('title', '') for link in external_links
    )

    if target_version == '9':
        assert rhel8to9_present
    else:
        assert not rhel8to9_present


@pytest.mark.parametrize(('result_expected', 'key', 'value'), (
    (True, 'net.ifnames', None),
    (True, 'net.ifnames', '0'),
    (False, 'net.ifname', None),
    (False, 'inet.ifnames', None),
    (False, 'missing', None),
    (False, 'missing', 'whatever'),
    (False, 'net.ifnames', '1'),
))
def test_is_kernel_arg_present(monkeypatch, result_expected, key, value):
    k_args = [
        KernelCmdlineArg(key='Foo', value='0'),
        KernelCmdlineArg(key='net.ifnames', value='0'),
        KernelCmdlineArg(key='Something', value='None'),
    ]
    curr_actor_mocked = CurrentActorMocked(
        msgs=[KernelCmdline(parameters=k_args)]
    )
    monkeypatch.setattr(persistentnetnamesdisable.api, 'current_actor', curr_actor_mocked)
    assert result_expected is persistentnetnamesdisable.is_kernel_arg_present(key, value)


@pytest.mark.parametrize(('naming_expected', 'k_args'), (
    (False, [KernelCmdlineArg(key='net.ifnames', value='0')]),
    (True, [KernelCmdlineArg(key='net.ifnames', value='1')]),
    (True, [KernelCmdlineArg(key='net.naming-scheme-foo', value='rhel-8.10')]),
    (
        # NOTE(pstodulk): this is kind of nonsense, but let's test it
        False,
        [
            KernelCmdlineArg(key='net.naming-scheme', value='rhel-8.10'),
            KernelCmdlineArg(key='net.ifnames', value='0'),
        ]
    ),
    (False, [KernelCmdlineArg(key='net.naming-scheme', value='rhel-8.10')]),
    (False, [KernelCmdlineArg(key='net.naming-scheme', value='rhel-9.10')]),
))
@pytest.mark.parametrize('src_ver', ('8.10', '9.8', '10.6'))
def test_report_ethx_ifaces_scheme(monkeypatch, naming_expected,  src_ver, k_args):
    _v_split = src_ver.split('.')
    dst_ver = '{}.{}'.format(int(_v_split[0]) + 1, _v_split[1])
    curr_actor_mocked = CurrentActorMocked(
        msgs=[KernelCmdline(parameters=k_args)],
        src_ver=src_ver,
        dst_ver=dst_ver
    )
    monkeypatch.setattr(persistentnetnamesdisable, 'create_report', create_report_mocked())
    monkeypatch.setattr(persistentnetnamesdisable.api, 'current_actor', curr_actor_mocked)

    persistentnetnamesdisable.report_ethX_ifaces()
    assert persistentnetnamesdisable.create_report.called
    report = persistentnetnamesdisable.create_report.reports[0]

    if naming_expected:
        url = 'https://red.ht/rhel-{}-consistent-nic-naming'.format(_v_split[0])
        assert any(url == link['url'] for link in report['detail']['external'])
        assert 'net.naming-scheme' in report['detail']['remediations'][0]['context']
    else:
        url_str = 'consistent-nic-naming'
        assert not any(url_str in link['url'] for link in report['detail']['external'])
        assert 'net.naming-scheme' not in report['detail']['remediations'][0]['context']
