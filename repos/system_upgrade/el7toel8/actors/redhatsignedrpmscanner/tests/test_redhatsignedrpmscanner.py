from leapp.snactor.fixture import current_actor_context
from leapp.models import RPM, InstalledRPM, InstalledRedHatSignedRPM, InstalledUnsignedRPM, CheckResult


RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


def test_actor_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(InstalledRedHatSignedRPM)


def test_actor_execution_with_signed_unsigned_data(current_actor_context):
    installed_rpm = [
        RPM(name='sample01', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
        RPM(name='sample02', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample03', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 5326810137017186'),
        RPM(name='sample04', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample05', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 938a80caf21541eb'),
        RPM(name='sample06', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample07', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID fd372689897da07a'),
        RPM(name='sample08', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample09', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 45689c882fa658e0')]

    current_actor_context.feed(InstalledRPM(items=installed_rpm))
    current_actor_context.run()
    assert current_actor_context.consume(InstalledRedHatSignedRPM)
    assert len(current_actor_context.consume(InstalledRedHatSignedRPM)[0].items) == 5
    assert current_actor_context.consume(InstalledUnsignedRPM)
    assert len(current_actor_context.consume(InstalledUnsignedRPM)[0].items) == 4

def test_gpg_pubkey_pkg(current_actor_context):
    installed_rpm = [
        RPM(name='gpg-pubkey', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID aa17105e03152d37'),
        RPM(name='gpg-pubkey', version='0.1', release='1.sm01', epoch='1', packager='Tester', arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 9ea903b1361e896b'),
    ]

    current_actor_context.feed(InstalledRPM(items=installed_rpm))
    current_actor_context.run()
    assert current_actor_context.consume(InstalledRedHatSignedRPM)
    assert len(current_actor_context.consume(InstalledRedHatSignedRPM)[0].items) == 1
    assert current_actor_context.consume(InstalledUnsignedRPM)
    assert len(current_actor_context.consume(InstalledUnsignedRPM)[0].items) == 1
