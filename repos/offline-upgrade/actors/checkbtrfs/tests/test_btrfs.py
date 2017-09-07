from leapp.snactor.fixture import current_actor_context
from leapp.models import ActiveKernelModule, SystemFacts, CheckResult


def test_actor_with_btrfs_module(current_actor_context):
    with_btrfs = [
        ActiveKernelModule(filename='btrfs'),
        ActiveKernelModule(filename='kvm')]

    current_actor_context.feed(SystemFacts(kernel_modules=with_btrfs))
    current_actor_context.run()
    assert current_actor_context.consume(CheckResult)


def test_actor_without_btrfs_module(current_actor_context):
    without_btrfs = [
        ActiveKernelModule(filename='kvm_intel'),
        ActiveKernelModule(filename='kvm')]

    current_actor_context.feed(SystemFacts(kernel_modules=without_btrfs))
    current_actor_context.run()
    assert not current_actor_context.consume(CheckResult)

