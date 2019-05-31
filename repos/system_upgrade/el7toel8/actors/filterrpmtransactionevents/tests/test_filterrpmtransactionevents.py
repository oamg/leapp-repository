from leapp.snactor.fixture import current_actor_context
from leapp.models import RPM, InstalledRedHatSignedRPM, FilteredRpmTransactionTasks, RpmTransactionTasks


RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


def test_actor_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(FilteredRpmTransactionTasks)


def test_actor_execution_with_sample_data(current_actor_context):
    installed_rpm = [
        RPM(name='sample01', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='SOME_PGP_SIG'),
        RPM(name='sample02', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
            pgpsig='SOME_PGP_SIG')]
    current_actor_context.feed(InstalledRedHatSignedRPM(items=installed_rpm))
    current_actor_context.feed(RpmTransactionTasks(
        to_remove=[rpm.name for rpm in installed_rpm],
        to_keep=[installed_rpm[0].name]
    ))
    current_actor_context.run()
    result = current_actor_context.consume(FilteredRpmTransactionTasks)
    assert len(result) == 1
    assert result[0].to_keep == [installed_rpm[0].name]
    assert result[0].to_remove == [installed_rpm[1].name]
