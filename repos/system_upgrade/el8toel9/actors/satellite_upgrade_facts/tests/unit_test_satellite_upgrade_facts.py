from leapp.libraries.common.config import mock_configs
from leapp.models import (
    InstalledRPM,
    RepositoriesSetupTasks,
    RPM,
    RpmTransactionTasks,
    SatelliteFacts,
    UsedRepositories,
    UsedRepository
)

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


def fake_package(pkg_name):
    return RPM(name=pkg_name, version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
               pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')


FOREMAN_RPM = fake_package('foreman')
FOREMAN_PROXY_RPM = fake_package('foreman-proxy')
KATELLO_INSTALLER_RPM = fake_package('foreman-installer-katello')
KATELLO_RPM = fake_package('katello')
RUBYGEM_KATELLO_RPM = fake_package('rubygem-katello')
RUBYGEM_FOREMAN_PUPPET_RPM = fake_package('rubygem-foreman_puppet')
POSTGRESQL_RPM = fake_package('postgresql-server')
SATELLITE_RPM = fake_package('satellite')
SATELLITE_CAPSULE_RPM = fake_package('satellite-capsule')

SATELLITE_REPOSITORY = UsedRepository(repository='satellite-6.99-for-rhel-8-x86_64-rpms')
CAPSULE_REPOSITORY = UsedRepository(repository='satellite-capsule-6.99-for-rhel-8-x86_64-rpms')
MAINTENANCE_REPOSITORY = UsedRepository(repository='satellite-maintenance-6.99-for-rhel-8-x86_64-rpms')


def test_no_satellite_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[]))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    message = current_actor_context.consume(SatelliteFacts)
    assert not message


def test_satellite_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM]))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    message = current_actor_context.consume(SatelliteFacts)[0]
    assert message.has_foreman


def test_wrong_arch(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM]))
    current_actor_context.run(config_model=mock_configs.CONFIG_S390X)
    message = current_actor_context.consume(SatelliteFacts)
    assert not message


def test_satellite_capsule_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_PROXY_RPM]))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    message = current_actor_context.consume(SatelliteFacts)[0]
    assert message.has_foreman


def test_no_katello_installer_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM]))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    message = current_actor_context.consume(SatelliteFacts)[0]
    assert not message.has_katello_installer


def test_katello_installer_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM, KATELLO_INSTALLER_RPM]))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    message = current_actor_context.consume(SatelliteFacts)[0]
    # while the katello installer rpm is present, we do not want this to be true
    # as the version in EL8 doesn't have the system checks we skip with this flag
    assert not message.has_katello_installer


def test_installs_related_package(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM, KATELLO_RPM, RUBYGEM_KATELLO_RPM,
                                                   RUBYGEM_FOREMAN_PUPPET_RPM]))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    message = current_actor_context.consume(RpmTransactionTasks)[0]
    assert 'katello' in message.to_install
    assert 'rubygem-katello' in message.to_install
    assert 'rubygem-foreman_puppet' in message.to_install


def test_installs_satellite_package(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM, SATELLITE_RPM]))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    message = current_actor_context.consume(RpmTransactionTasks)[0]
    assert 'satellite' in message.to_install
    assert 'satellite-capsule' not in message.to_install


def test_installs_satellite_capsule_package(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_PROXY_RPM, SATELLITE_CAPSULE_RPM]))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    message = current_actor_context.consume(RpmTransactionTasks)[0]
    assert 'satellite-capsule' in message.to_install
    assert 'satellite' not in message.to_install


def test_detects_local_postgresql(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM, POSTGRESQL_RPM]))
    current_actor_context.run(config_model=mock_configs.CONFIG)

    satellitemsg = current_actor_context.consume(SatelliteFacts)[0]
    assert satellitemsg.postgresql.local_postgresql


def test_detects_remote_postgresql(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM]))
    current_actor_context.run(config_model=mock_configs.CONFIG)

    satellitemsg = current_actor_context.consume(SatelliteFacts)[0]
    assert not satellitemsg.postgresql.local_postgresql


def test_enables_right_repositories_on_satellite(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM, SATELLITE_RPM]))
    current_actor_context.feed(UsedRepositories(repositories=[SATELLITE_REPOSITORY, MAINTENANCE_REPOSITORY]))
    current_actor_context.run(config_model=mock_configs.CONFIG)

    rpmmessage = current_actor_context.consume(RepositoriesSetupTasks)[0]

    assert 'satellite-maintenance-6.99-for-rhel-9-x86_64-rpms' in rpmmessage.to_enable
    assert 'satellite-6.99-for-rhel-9-x86_64-rpms' in rpmmessage.to_enable
    assert 'satellite-capsule-6.99-for-rhel-9-x86_64-rpms' not in rpmmessage.to_enable


def test_enables_right_repositories_on_capsule(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_PROXY_RPM, SATELLITE_CAPSULE_RPM]))
    current_actor_context.feed(UsedRepositories(repositories=[CAPSULE_REPOSITORY, MAINTENANCE_REPOSITORY]))
    current_actor_context.run(config_model=mock_configs.CONFIG)

    rpmmessage = current_actor_context.consume(RepositoriesSetupTasks)[0]

    assert 'satellite-maintenance-6.99-for-rhel-9-x86_64-rpms' in rpmmessage.to_enable
    assert 'satellite-6.99-for-rhel-9-x86_64-rpms' not in rpmmessage.to_enable
    assert 'satellite-capsule-6.99-for-rhel-9-x86_64-rpms' in rpmmessage.to_enable


def test_enables_right_repositories_on_upstream(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM]))
    current_actor_context.run(config_model=mock_configs.CONFIG)

    message = current_actor_context.consume(RepositoriesSetupTasks)

    assert not message
