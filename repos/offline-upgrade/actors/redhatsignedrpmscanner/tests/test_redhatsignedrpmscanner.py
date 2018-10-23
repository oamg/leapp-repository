from leapp.snactor.fixture import current_actor_context
from leapp.models import RPM, InstalledRPM, InstalledRedHatSignedRPM, CheckResult

def test_actor_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(InstalledRedHatSignedRPM)

def test_actor_execution_with_signed_data(current_actor_context):
    installed_rpm = [
        RPM(name='sample01', version='0.1', release='1.sm01', epoch='1', arch='noarch', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
        RPM(name='sample03', version='0.1', release='1.sm01', epoch='1', arch='noarch', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 5326810137017186'),
        RPM(name='sample05', version='0.1', release='1.sm01', epoch='1', arch='noarch', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 938a80caf21541eb'),
        RPM(name='sample07', version='0.1', release='1.sm01', epoch='1', arch='noarch', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID fd372689897da07a'),
        RPM(name='sample09', version='0.1', release='1.sm01', epoch='1', arch='noarch', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 45689c882fa658e0')]

    current_actor_context.feed(InstalledRPM(items=installed_rpm))
    current_actor_context.run()
    assert current_actor_context.consume(InstalledRedHatSignedRPM)
    assert len(current_actor_context.consume(InstalledRedHatSignedRPM)[0].items) == 5

def test_actor_execution_with_not_signed_data(current_actor_context):
    installed_rpm = [
        RPM(name='sample02', version='0.1', release='1.sm01', epoch='1', arch='noarch', pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample04', version='0.1', release='1.sm01', epoch='1', arch='noarch', pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample06', version='0.1', release='1.sm01', epoch='1', arch='noarch', pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample08', version='0.1', release='1.sm01', epoch='1', arch='noarch', pgpsig='SOME_OTHER_SIG_X')]

    current_actor_context.feed(InstalledRPM(items=installed_rpm))
    current_actor_context.run()
    assert current_actor_context.consume(CheckResult)
    assert current_actor_context.consume(CheckResult)[0].severity == 'Error'
