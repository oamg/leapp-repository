from leapp import reporting
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, SystemdServicesInfoSource

DHCP_SERVER_PACKAGE = 'dhcp-server'
DHCP_SERVICES = ('dhcpd.service', 'dhcpd6.service')
ENABLED_STATES = ('enabled', 'enabled-runtime')


def _enabled_dhcp_services():
    """
    Return names of the ISC DHCP services that are enabled on the source system.
    """
    services_info = next(api.consume(SystemdServicesInfoSource), None)
    if not services_info:
        return []
    return [
        service.name for service in services_info.service_files
        if service.name in DHCP_SERVICES and service.state in ENABLED_STATES
    ]


def _report_dhcp_server_in_use(services):
    target_distro = DISTRO_REPORT_NAMES['target_distro']
    summary = (
        f'ISC DHCP ({DHCP_SERVER_PACKAGE}) is installed and its service ({", ".join(services)})'
        ' is enabled on this system.'
        f' ISC DHCP has reached end-of-life and is not available in {target_distro} 10.'
        ' The system must be migrated to ISC Kea; otherwise the DHCP server'
        ' will be removed during the upgrade and DHCP will stop being served.'
    )

    reporting.create_report([
        reporting.Title('ISC DHCP is not available on the target system'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.NETWORK]),
        reporting.Remediation(
            hint='Migrate from ISC DHCP to ISC Kea following the ISC migration guide.'
        ),
        reporting.ExternalLink(
            title='Migrating from ISC DHCP to Kea DHCP using the Migration Assistant',
            url='https://kb.isc.org/docs/migrating-from-isc-dhcp-to-kea-dhcp-using-the-migration-assistant'
        ),
        reporting.ExternalLink(
            title='ISC DHCP migration overview',
            url='https://www.isc.org/dhcp_migration/'
        ),
        reporting.RelatedResource('package', DHCP_SERVER_PACKAGE),
    ] + [reporting.RelatedResource('service', service) for service in services])


def process():
    if not has_package(DistributionSignedRPM, DHCP_SERVER_PACKAGE):
        return

    services = _enabled_dhcp_services()
    if services:
        _report_dhcp_server_in_use(services)
