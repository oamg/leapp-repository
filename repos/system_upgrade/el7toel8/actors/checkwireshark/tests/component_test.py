from leapp.snactor.fixture import current_actor_context
from leapp.models import InstalledRedHatSignedRPM, RPM
from leapp.reporting import Report

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


def test_actor_with_grep_package(current_actor_context):
    rpms = [
        RPM(name='wireshark', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
        RPM(name='powertop', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')]

    current_actor_context.feed(InstalledRedHatSignedRPM(items=rpms))
    current_actor_context.run()
    assert current_actor_context.consume(Report)


def test_actor_without_grep_package(current_actor_context):
    rpms = [
        RPM(name='powertop', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
        RPM(name='sed', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')]

    current_actor_context.feed(InstalledRedHatSignedRPM(items=rpms))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
