from leapp.snactor.fixture import current_actor_context
from leapp.models import RPM, InstalledUnsignedRPM, CheckResult


def test_actor_execution(current_actor_context):
    current_actor_context.feed(InstalledUnsignedRPM(items=[]))
    current_actor_context.run()
    assert not current_actor_context.consume(CheckResult)


def test_actor_execution_with_unsigned_data(current_actor_context):
    installed_rpm = [
        RPM(name='sample02', version='0.1', release='1.sm01', epoch='1', arch='noarch', pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample04', version='0.1', release='1.sm01', epoch='1', arch='noarch', pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample06', version='0.1', release='1.sm01', epoch='1', arch='noarch', pgpsig='SOME_OTHER_SIG_X'),
        RPM(name='sample08', version='0.1', release='1.sm01', epoch='1', arch='noarch', pgpsig='SOME_OTHER_SIG_X')]

    current_actor_context.feed(InstalledUnsignedRPM(items=installed_rpm))
    current_actor_context.run()
    assert current_actor_context.consume(CheckResult)
