import os

from leapp.models import (
    DNFWorkaround,
    InstalledRPM,
    Module,
    RepositoriesSetupTasks,
    RPM,
    RpmTransactionTasks,
    SatelliteFacts
)
from leapp.snactor.fixture import current_actor_context

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


def fake_package(pkg_name):
    return RPM(name=pkg_name, version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
               pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')


FOREMAN_RPM = fake_package('foreman')
FOREMAN_PROXY_RPM = fake_package('foreman-proxy')
KATELLO_RPM = fake_package('katello')
POSTGRESQL_RPM = fake_package('rh-postgresql12-postgresql-server')


def test_no_satellite_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[]))
    current_actor_context.run()
    message = current_actor_context.consume(SatelliteFacts)
    assert not message


def test_satellite_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM]))
    current_actor_context.run()
    message = current_actor_context.consume(SatelliteFacts)[0]
    assert message.has_foreman


def test_satellite_capsule_present(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_PROXY_RPM]))
    current_actor_context.run()
    message = current_actor_context.consume(SatelliteFacts)[0]
    assert message.has_foreman


def test_enables_ruby_module(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM]))
    current_actor_context.run()
    message = current_actor_context.consume(RpmTransactionTasks)[0]
    assert Module(name='ruby', stream='2.7') in message.modules_to_enable


def test_enables_pki_modules(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM, KATELLO_RPM]))
    current_actor_context.run()
    message = current_actor_context.consume(RpmTransactionTasks)[0]
    assert Module(name='pki-core', stream='10.6') in message.modules_to_enable
    assert Module(name='pki-deps', stream='10.6') in message.modules_to_enable


def test_detects_local_postgresql(monkeypatch, current_actor_context):
    def mock_stat():
        orig_stat = os.stat

        def mocked_stat(path):
            if path == '/var/opt/rh/rh-postgresql12/lib/pgsql/data/':
                path = '/'
            return orig_stat(path)
        return mocked_stat
    monkeypatch.setattr("os.stat", mock_stat())

    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM, POSTGRESQL_RPM]))
    current_actor_context.run()

    rpmmessage = current_actor_context.consume(RpmTransactionTasks)[0]
    assert Module(name='postgresql', stream='12') in rpmmessage.modules_to_enable

    satellitemsg = current_actor_context.consume(SatelliteFacts)[0]
    assert satellitemsg.postgresql.local_postgresql

    assert current_actor_context.consume(DNFWorkaround)


def test_detects_remote_postgresql(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM]))
    current_actor_context.run()

    rpmmessage = current_actor_context.consume(RpmTransactionTasks)[0]
    assert Module(name='postgresql', stream='12') not in rpmmessage.modules_to_enable

    satellitemsg = current_actor_context.consume(SatelliteFacts)[0]
    assert not satellitemsg.postgresql.local_postgresql

    assert not current_actor_context.consume(DNFWorkaround)


def test_enables_right_repositories_on_satellite(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_RPM]))
    current_actor_context.run()

    rpmmessage = current_actor_context.consume(RepositoriesSetupTasks)[0]

    assert 'ansible-2.9-for-rhel-8-x86_64-rpms' in rpmmessage.to_enable
    assert 'satellite-maintenance-6.11-for-rhel-8-x86_64-rpms' in rpmmessage.to_enable
    assert 'satellite-6.11-for-rhel-8-x86_64-rpms' in rpmmessage.to_enable
    assert 'satellite-capsule-6.11-for-rhel-8-x86_64-rpms' not in rpmmessage.to_enable


def test_enables_right_repositories_on_capsule(current_actor_context):
    current_actor_context.feed(InstalledRPM(items=[FOREMAN_PROXY_RPM]))
    current_actor_context.run()

    rpmmessage = current_actor_context.consume(RepositoriesSetupTasks)[0]

    assert 'ansible-2.9-for-rhel-8-x86_64-rpms' in rpmmessage.to_enable
    assert 'satellite-maintenance-6.11-for-rhel-8-x86_64-rpms' in rpmmessage.to_enable
    assert 'satellite-6.11-for-rhel-8-x86_64-rpms' not in rpmmessage.to_enable
    assert 'satellite-capsule-6.11-for-rhel-8-x86_64-rpms' in rpmmessage.to_enable
