from leapp.snactor.fixture import current_actor_context
from leapp.models import InstalledRedHatSignedRPM, RPM
from leapp.reporting import Report

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'
GPGSIGN = (
    'RSA/SHA256, Mon 01 Jan 1970 '
    '00:00:00 AM -03, Key ID 199e2f91fd431d51'
)


def create_modulesfacts(installed_rpm):
    return InstalledRedHatSignedRPM(items=installed_rpm)


def test_actor_with_dhclient(current_actor_context):
    with_dhclient = [
        RPM(name='dhclient',
            version='0.1',
            release='1.el8',
            epoch='1',
            packager=RH_PACKAGER,
            arch='noarch',
            pgpsig=GPGSIGN),
        RPM(name='dhcp-client',
            version='0.1',
            release='1.fc1',
            epoch='1',
            packager=RH_PACKAGER,
            arch='noarch',
            pgpsig=GPGSIGN)]

    current_actor_context.feed(create_modulesfacts(installed_rpm=with_dhclient))
    current_actor_context.run()
    assert len(current_actor_context.consume(Report)) > 0


def test_actor_without_dhclient(current_actor_context):
    without_dhclient = [
        RPM(name='bind',
            version='0.1',
            release='1.el1',
            epoch='1',
            packager=RH_PACKAGER,
            arch='noarch',
            pgpsig=GPGSIGN),
        RPM(name='kernel',
            version='0.1',
            release='1',
            epoch='1',
            packager=RH_PACKAGER,
            arch='noarch',
            pgpsig=GPGSIGN)]

    current_actor_context.feed(create_modulesfacts(installed_rpm=without_dhclient))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
