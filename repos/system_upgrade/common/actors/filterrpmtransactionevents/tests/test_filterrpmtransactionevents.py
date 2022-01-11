from leapp.models import FilteredRpmTransactionTasks, InstalledRedHatSignedRPM, Module, RPM, RpmTransactionTasks
from leapp.snactor.fixture import current_actor_context

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
    modules_to_enable = [Module(name='enable', stream='1'), Module(name='enable', stream='2')]
    modules_to_reset = [Module(name='reset', stream='1'), Module(name='reset', stream='2')]
    current_actor_context.feed(InstalledRedHatSignedRPM(items=installed_rpm))
    current_actor_context.feed(RpmTransactionTasks(
        to_remove=[rpm.name for rpm in installed_rpm],
        to_keep=[installed_rpm[0].name],
        modules_to_enable=modules_to_enable,
        modules_to_reset=modules_to_reset,
    ))
    current_actor_context.feed(RpmTransactionTasks(
        modules_to_enable=modules_to_enable,
        modules_to_reset=modules_to_reset,
    ))
    current_actor_context.run()
    result = current_actor_context.consume(FilteredRpmTransactionTasks)
    assert len(result) == 1
    assert result[0].to_keep == [installed_rpm[0].name]
    assert result[0].to_remove == [installed_rpm[1].name]

    assert len(result[0].modules_to_enable) == 2
    assert all(m.name == 'enable' for m in result[0].modules_to_enable)
    assert '1' in {m.stream for m in result[0].modules_to_enable}
    assert '2' in {m.stream for m in result[0].modules_to_enable}

    assert len(result[0].modules_to_reset) == 2
    assert all(m.name == 'reset' for m in result[0].modules_to_reset)
    assert '1' in {m.stream for m in result[0].modules_to_reset}
    assert '2' in {m.stream for m in result[0].modules_to_reset}
