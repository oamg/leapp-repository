from leapp.models import ActiveKernelModule, ActiveKernelModulesFacts
from leapp.reporting import Report
from leapp.utils.report import is_inhibitor


def test_actor_with_nvidia_driver(current_actor_context):
    with_nvidia = [
        ActiveKernelModule(filename='nvidia', parameters=[]),
        ActiveKernelModule(filename='kvm', parameters=[])]

    current_actor_context.feed(ActiveKernelModulesFacts(kernel_modules=with_nvidia))
    current_actor_context.run()
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)


def test_actor_without_nvidia_driver(current_actor_context):
    without_nvidia = [
        ActiveKernelModule(filename='i915', parameters=[]),
        ActiveKernelModule(filename='kvm', parameters=[])]

    current_actor_context.feed(ActiveKernelModulesFacts(kernel_modules=without_nvidia))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_with_nouveau_driver(current_actor_context):
    without_nvidia = [
        ActiveKernelModule(filename='nouveau', parameters=[]),
        ActiveKernelModule(filename='kvm', parameters=[])]

    current_actor_context.feed(ActiveKernelModulesFacts(kernel_modules=without_nvidia))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
