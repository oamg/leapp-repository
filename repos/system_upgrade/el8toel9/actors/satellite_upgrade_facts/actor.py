from leapp.actors import Actor
from leapp.libraries.common.config import architecture
from leapp.libraries.common.rpms import has_package
from leapp.models import (
    InstalledRPM,
    RepositoriesSetupTasks,
    RpmTransactionTasks,
    SatelliteFacts,
    SatellitePostgresqlFacts,
    UsedRepositories
)
from leapp.tags import FactsPhaseTag, IPUWorkflowTag

RELATED_PACKAGES = ('foreman', 'foreman-selinux', 'foreman-proxy', 'katello', 'katello-selinux',
                    'candlepin', 'candlepin-selinux', 'pulpcore-selinux', 'satellite', 'satellite-capsule')
RELATED_PACKAGE_PREFIXES = ('rubygem-hammer', 'rubygem-foreman', 'rubygem-katello',
                            'rubygem-smart_proxy', 'python3.11-pulp', 'foreman-installer',
                            'satellite-installer')


class SatelliteUpgradeFacts(Actor):
    """
    Report which Satellite packages require updates and how to handle PostgreSQL data
    """

    name = 'satellite_upgrade_facts'
    consumes = (InstalledRPM, UsedRepositories)
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
                has_pulp_ansible_semver=has_package(InstalledRPM, 'python3.11-pulp-ansible'),
            ),
        ))

        repositories_to_enable = []
        for used_repos in self.consume(UsedRepositories):
            for used_repo in used_repos.repositories:
                if used_repo.repository.startswith(('satellite-6', 'satellite-capsule-6', 'satellite-maintenance-6')):
                    repositories_to_enable.append(used_repo.repository.replace('for-rhel-8', 'for-rhel-9'))
        if repositories_to_enable:
            self.produce(RepositoriesSetupTasks(to_enable=repositories_to_enable))

        self.produce(RpmTransactionTasks(to_install=to_install))
