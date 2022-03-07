from leapp.models import InstalledRPM, RPM
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context


def test_actor_with_docker_package(current_actor_context):
    with_docker = [
            RPM(name='docker',
                epoch='2',
                packager='Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>',
                version='1.13.1',
                release='209.git7d71120.el7_9',
                arch='x86_64',
                pgpsig='RSA/SHA256, Fri 07 Jan 2022 01:50:17 PM UTC, Key ID 199e2f91fd431d51',
                repository='installed',
                module=None,
                stream=None),
            RPM(name='grep',
                epoch='0',
                packager='Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>',
                version='2.20',
                release='3.el7',
                arch='x86_64',
                pgpsig='RSA/SHA256, Fri 24 Mar 2017 04:59:11 PM UTC, Key ID 199e2f91fd431d51',
                repository='anaconda/7.9',
                module=None,
                stream=None)
            ]

    current_actor_context.feed(InstalledRPM(items=with_docker))
    current_actor_context.run()
    assert current_actor_context.consume(Report)


def test_actor_without_docker_package(current_actor_context):
    without_docker = [
            RPM(name='tree',
                epoch='0',
                packager='Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>',
                version='1.6.0',
                release='10.el7',
                arch='x86_64',
                pgpsig='RSA/SHA256, Wed 02 Apr 2014 09:33:48 PM UTC, Key ID 199e2f91fd431d51',
                repository='installed',
                module=None,
                stream=None),
            RPM(name='grep',
                epoch='0',
                packager='Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>',
                version='2.20',
                release='3.el7',
                arch='x86_64',
                pgpsig='RSA/SHA256, Fri 24 Mar 2017 04:59:11 PM UTC, Key ID 199e2f91fd431d51',
                repository='anaconda/7.9',
                module=None,
                stream=None)
            ]

    current_actor_context.feed(InstalledRPM(items=without_docker))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
