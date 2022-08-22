from leapp.models import BrlttyMigrationDecision, InstalledRedHatSignedRPM, RPM
from leapp.reporting import Report

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'

with_brltty = [
    RPM(name='grep', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
        pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
    RPM(name='brltty', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
        pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')]

without_brltty = [
    RPM(name='grep', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
        pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
    RPM(name='sed', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
        pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')]


def create_modulesfacts(installed_rpm):
    return InstalledRedHatSignedRPM(items=installed_rpm)


def test_actor_without_brltty_package(current_actor_context):
    current_actor_context.feed(create_modulesfacts(installed_rpm=without_brltty))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_with_brltty_package(current_actor_context):
    current_actor_context.feed(create_modulesfacts(installed_rpm=with_brltty))
    current_actor_context.run()
    assert current_actor_context.consume(Report)
