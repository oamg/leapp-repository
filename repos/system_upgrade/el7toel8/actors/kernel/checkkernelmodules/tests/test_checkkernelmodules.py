from leapp.models import ActiveKernelModulesFacts, ActiveKernelModule, KernelModuleParameter, WhitelistedKernelModules
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
    assert not current_actor_context.consume(Report)


def test_actor_with_whitelisted_modules(current_actor_context):
    """ Tests CheckKernelModules actor by feeding it kernel modules that
    are whitelisted in the WhitelistKernelModule actor. Actor should NOT produce
    any report.
    """
    modules = WhitelistedKernelModules(whitelisted_modules=["cryptd", "floppy"])
    current_actor_context.feed(modules)
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
