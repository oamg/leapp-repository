from leapp.models import ActiveKernelModulesFacts, ActiveKernelModule, KernelModuleParameter
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context


def test_actor_with_missing_modules(current_actor_context):
    """ Tests CheckKernelModules actor by feeding it kernel modules that
    are not available on the RHEL8 system. Actor should produce inhibitor.
    """
    modules = [ActiveKernelModule(filename="virtio", parameters=[]),
               ActiveKernelModule(filename="aoe", parameters=[])]
    current_actor_context.feed(ActiveKernelModulesFacts(kernel_modules=modules))
    current_actor_context.run()
    assert "inhibitor" in current_actor_context.consume(Report)[0].flags


def test_actor_without_missing_modules(current_actor_context):
    """ Tests CheckKernelModules actor by feeding it kernel modules that
    are available on the RHEL8 system. Actor should NOT produce any report.
    """
    modules = [ActiveKernelModule(filename="foobar", parameters=[]),
               ActiveKernelModule(filename="barfoo", parameters=[])]
    current_actor_context.feed(ActiveKernelModulesFacts(kernel_modules=modules))
    current_actor_context.run()
    assert len(current_actor_context.consume(Report)) == 0
