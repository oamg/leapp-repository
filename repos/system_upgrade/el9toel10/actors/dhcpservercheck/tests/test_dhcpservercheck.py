import pytest

from leapp import reporting
from leapp.libraries.actor import dhcpservercheck
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RPM, SystemdServiceFile, SystemdServicesInfoSource
from leapp.utils.report import is_inhibitor


def _rpm(name):
    return RPM(name=name,
               version='0.1',
               release='1.sm01',
               epoch='1',
               pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51',
               packager='Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>',
               arch='noarch')


def _services(**states):
    return SystemdServicesInfoSource(
        service_files=[SystemdServiceFile(name=name, state=state) for name, state in states.items()]
    )


@pytest.mark.parametrize('pkg, service_states, expect_report', [
    ('dhcp-server', {'dhcpd.service': 'enabled'}, True),
    ('dhcp-server', {'dhcpd.service': 'enabled-runtime'}, True),
    ('dhcp-server', {'dhcpd6.service': 'enabled'}, True),
    ('dhcp-server', {'dhcpd.service': 'disabled'}, False),
    ('dhcp-server', {'dhcpd.service': 'masked'}, False),
    ('dhcp-server', {'sshd.service': 'enabled'}, False),
    ('dhcp-server', {}, False),
    ('sed', {'dhcpd.service': 'enabled'}, False),
])
def test_process(monkeypatch, pkg, service_states, expect_report):
    msgs = [DistributionSignedRPM(items=[_rpm('bash'), _rpm(pkg)]), _services(**service_states)]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    dhcpservercheck.process()

    assert bool(reporting.create_report.called) == expect_report


def test_process_no_services_info(monkeypatch):
    msgs = [DistributionSignedRPM(items=[_rpm('dhcp-server')])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    dhcpservercheck.process()

    assert not reporting.create_report.called


def test_report_content(monkeypatch):
    msgs = [DistributionSignedRPM(items=[_rpm('dhcp-server')]), _services(**{'dhcpd.service': 'enabled'})]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    dhcpservercheck.process()

    assert reporting.create_report.called == 1
    report = reporting.create_report.report_fields
    assert 'ISC DHCP is not available on the target system' in report['title']
    assert report['severity'] == reporting.Severity.HIGH
    assert not is_inhibitor(report)
    assert 'dhcpd.service' in report['summary']
    assert 'Kea' in report['detail']['remediations'][0]['context']
    assert any('isc.org' in link['url'] for link in report['detail']['external'])
