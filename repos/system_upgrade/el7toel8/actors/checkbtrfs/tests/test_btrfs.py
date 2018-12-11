from leapp.snactor.fixture import current_actor_context
from leapp.models import ActiveKernelModule, SystemFacts, CheckResult

# import needed just to be able to create valid model, but not important for test
from leapp.models import FirewallStatus, Firewalls, SELinux

def create_selinux(static_mode, enabled, policy='targeted', mls_enabled=True):
    runtime_mode = static_mode if static_mode != 'disabled' else None

    return SELinux(
            runtime_mode=runtime_mode,
            static_mode=static_mode,
            enabled=enabled,
            policy=policy,
            mls_enabled=mls_enabled,
        )


def create_sysfacts(kernel_modules):
    return SystemFacts(
            sysctl_variables=[],
            kernel_modules=kernel_modules,
            users=[],
            groups=[],
            repositories=[],
            selinux=create_selinux(static_mode='permissive', enabled=True),
            firewalls=Firewalls(
                firewalld=FirewallStatus(enabled=True, active=True),
                iptables=FirewallStatus(enabled=True, active=True),
            ),
        )


def test_actor_with_btrfs_module(current_actor_context):
    with_btrfs = [
        ActiveKernelModule(filename='btrfs', parameters=[]),
        ActiveKernelModule(filename='kvm', parameters=[])]

    current_actor_context.feed(create_sysfacts(kernel_modules=with_btrfs))
    current_actor_context.run()
    assert current_actor_context.consume(CheckResult)


def test_actor_without_btrfs_module(current_actor_context):
    without_btrfs = [
        ActiveKernelModule(filename='kvm_intel', parameters=[]),
        ActiveKernelModule(filename='kvm', parameters=[])]

    current_actor_context.feed(create_sysfacts(kernel_modules=without_btrfs))
    current_actor_context.run()
    assert not current_actor_context.consume(CheckResult)

