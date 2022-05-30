import os

from leapp.actors import Actor
from leapp.libraries.common.config import architecture
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import run
from leapp.models import (
    DNFWorkaround,
    InstalledRPM,
    Module,
    RepositoriesSetupTasks,
    RpmTransactionTasks,
    SatelliteFacts,
    SatellitePostgresqlFacts
)
from leapp.tags import FactsPhaseTag, IPUWorkflowTag

POSTGRESQL_SCL_DATA_PATH = '/var/opt/rh/rh-postgresql12/lib/pgsql/data/'


class SatelliteUpgradeFacts(Actor):
    """
    Report which Satellite packages require updates and how to handle PostgreSQL data
    """

    name = 'satellite_upgrade_facts'
    consumes = (InstalledRPM, )
    produces = (DNFWorkaround, RepositoriesSetupTasks, RpmTransactionTasks, SatelliteFacts)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        if not architecture.matches_architecture(architecture.ARCH_X86_64):
            return

        has_foreman = has_package(InstalledRPM, 'foreman') or has_package(InstalledRPM, 'foreman-proxy')
        if not has_foreman:
            return

        has_katello_installer = has_package(InstalledRPM, 'foreman-installer-katello')

        local_postgresql = has_package(InstalledRPM, 'rh-postgresql12-postgresql-server')
        postgresql_contrib = has_package(InstalledRPM, 'rh-postgresql12-postgresql-contrib')
        postgresql_evr = has_package(InstalledRPM, 'rh-postgresql12-postgresql-evr')

        to_remove = ['tfm-runtime', 'tfm-pulpcore-runtime', 'rh-redis5-runtime', 'rh-ruby27-runtime',
                     'rh-python38-runtime']
        to_install = ['rubygem-foreman_maintain']
        modules_to_enable = [Module(name='ruby', stream='2.7')]

        if has_package(InstalledRPM, 'katello'):
            # enable modules that are needed for Candlepin, which is pulled in by Katello
            modules_to_enable.append(Module(name='pki-core', stream='10.6'))
            modules_to_enable.append(Module(name='pki-deps', stream='10.6'))
            # enable modules that are needed for Pulpcore
            modules_to_enable.append(Module(name='python38', stream='3.8'))
            to_install.append('katello')

        if has_package(InstalledRPM, 'rh-redis5-redis'):
            modules_to_enable.append(Module(name='redis', stream='5'))
            to_install.append('redis')

        for rpm_pkgs in self.consume(InstalledRPM):
            for pkg in rpm_pkgs.items:
                if (pkg.name.startswith('tfm-rubygem-hammer') or pkg.name.startswith('tfm-rubygem-foreman')
                        or pkg.name.startswith('tfm-rubygem-katello')
                        or pkg.name.startswith('tfm-rubygem-smart_proxy')):
                    to_install.append(pkg.name.replace('tfm-rubygem-', 'rubygem-'))
                elif pkg.name.startswith('tfm-pulpcore-python3-pulp'):
                    to_install.append(pkg.name.replace('tfm-pulpcore-python3-', 'python38-'))
                elif pkg.name.startswith('foreman-installer') or pkg.name.startswith('satellite-installer'):
                    to_install.append(pkg.name)

        on_same_partition = True
        bytes_required = None
        bytes_available = None
        old_pgsql_data = False

        if local_postgresql:
            """
            Handle migration of the PostgreSQL legacy-actions files.
            RPM cannot handle replacement of directories by symlinks by default
            without the %pretrans scriptlet. As PostgreSQL package is packaged wrong,
            we have to workround that by migration of the PostgreSQL files
            before the rpm transaction is processed.
            """
            self.produce(
                DNFWorkaround(
                    display_name='PostgreSQL symlink fix',
                    script_path=self.get_tool_path('handle-postgresql-legacy-actions'),
                )
            )

            old_pgsql_data = bool(os.path.exists('/var/lib/pgsql/data/') and os.listdir('/var/lib/pgsql/data/')
                                  and os.path.exists(POSTGRESQL_SCL_DATA_PATH)
                                  and os.listdir(POSTGRESQL_SCL_DATA_PATH))
            scl_psql_stat = os.stat(POSTGRESQL_SCL_DATA_PATH)
            for nonscl_path in ['/var/lib/pgsql/data/', '/var/lib/pgsql/', '/var/lib/', '/']:
                if os.path.exists(nonscl_path):
                    nonscl_psql_stat = os.stat(nonscl_path)
                    break

            if scl_psql_stat.st_dev != nonscl_psql_stat.st_dev:
                on_same_partition = False
                # get the current disk usage of the PostgreSQL data
                scl_du_call = run(['du', '--block-size=1', '--summarize', POSTGRESQL_SCL_DATA_PATH])
                bytes_required = int(scl_du_call['stdout'].split()[0])
                # get the current free space on the target partition
                nonscl_stat = os.statvfs(nonscl_path)
                bytes_available = nonscl_stat.f_bavail * nonscl_stat.f_frsize

            modules_to_enable.append(Module(name='postgresql', stream='12'))
            to_remove.append('rh-postgresql12-runtime')
            to_install.extend(['postgresql', 'postgresql-server'])
            if postgresql_contrib:
                to_remove.append('rh-postgresql12-postgresql-contrib')
                to_install.append('postgresql-contrib')
            if postgresql_evr:
                to_remove.append('rh-postgresql12-postgresql-evr')
                to_install.append('postgresql-evr')

        self.produce(SatelliteFacts(
            has_foreman=has_foreman,
            has_katello_installer=has_katello_installer,
            postgresql=SatellitePostgresqlFacts(
                local_postgresql=local_postgresql,
                old_var_lib_pgsql_data=old_pgsql_data,
                same_partition=on_same_partition,
                space_required=bytes_required,
                space_available=bytes_available,
            ),
        ))

        repositories_to_enable = ['satellite-maintenance-6.11-for-rhel-8-x86_64-rpms']
        if has_package(InstalledRPM, 'satellite'):
            repositories_to_enable.append('satellite-6.11-for-rhel-8-x86_64-rpms')
            modules_to_enable.append(Module(name='satellite', stream='el8'))
        elif has_package(InstalledRPM, 'satellite-capsule'):
            repositories_to_enable.append('satellite-capsule-6.11-for-rhel-8-x86_64-rpms')
            modules_to_enable.append(Module(name='satellite-capsule', stream='el8'))

        self.produce(RpmTransactionTasks(
            to_remove=to_remove,
            to_install=to_install,
            modules_to_enable=modules_to_enable
            )
        )

        self.produce(RepositoriesSetupTasks(to_enable=repositories_to_enable))
