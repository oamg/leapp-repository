from leapp.actors import Actor
from leapp.libraries.common.config import architecture
from leapp.libraries.common.rpms import has_package
from leapp.models import (
    InstalledRPM,
    RepositoriesSetupTasks,
    RpmTransactionTasks,
    SatelliteFacts,
    SatellitePostgresqlFacts
)
from leapp.tags import FactsPhaseTag, IPUWorkflowTag

SATELLITE_VERSION = '6.99'

RELATED_PACKAGES = ('foreman', 'foreman-proxy', 'katello', 'candlepin')
RELATED_PACKAGE_PREFIXES = ('rubygem-hammer', 'rubygem-foreman', 'rubygem-katello',
                            'rubygem-smart_proxy', 'python3.11-pulp', 'foreman-installer',
                            'satellite-installer')


class SatelliteUpgradeFacts(Actor):
    """
    Report which Satellite packages require updates and how to handle PostgreSQL data
    """

    name = 'satellite_upgrade_facts'
    consumes = (InstalledRPM, )
    produces = (RepositoriesSetupTasks, RpmTransactionTasks, SatelliteFacts)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        if not architecture.matches_architecture(architecture.ARCH_X86_64):
            return

        has_foreman = has_package(InstalledRPM, 'foreman') or has_package(InstalledRPM, 'foreman-proxy')
        if not has_foreman:
            return

        local_postgresql = has_package(InstalledRPM, 'postgresql-server')

        to_install = ['rubygem-foreman_maintain']

        for rpm_pkgs in self.consume(InstalledRPM):
            for pkg in rpm_pkgs.items:
                if pkg.name in RELATED_PACKAGES or pkg.name.startswith(RELATED_PACKAGE_PREFIXES):
                    to_install.append(pkg.name)

        if local_postgresql:
            to_install.extend(['postgresql', 'postgresql-server'])
            if has_package(InstalledRPM, 'postgresql-contrib'):
                to_install.append('postgresql-contrib')
            if has_package(InstalledRPM, 'postgresql-evr'):
                to_install.append('postgresql-evr')

        self.produce(SatelliteFacts(
            has_foreman=has_foreman,
            has_katello_installer=False,
            postgresql=SatellitePostgresqlFacts(
                local_postgresql=local_postgresql,
            ),
        ))

        satellite = has_package(InstalledRPM, 'satellite')
        capsule = has_package(InstalledRPM, 'satellite-capsule')
        if satellite or capsule:
            repositories_to_enable = [f'satellite-maintenance-{SATELLITE_VERSION}-for-rhel-9-x86_64-rpms']
            if satellite:
                repositories_to_enable.append(f'satellite-{SATELLITE_VERSION}-for-rhel-9-x86_64-rpms')
                to_install.append('satellite')
            elif capsule:
                repositories_to_enable.append(f'satellite-capsule-{SATELLITE_VERSION}-for-rhel-9-x86_64-rpms')
                to_install.append('satellite-capsule')
            self.produce(RepositoriesSetupTasks(to_enable=repositories_to_enable))

        self.produce(RpmTransactionTasks(to_install=to_install))
