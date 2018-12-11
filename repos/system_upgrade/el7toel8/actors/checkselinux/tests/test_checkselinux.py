from leapp.snactor.fixture import current_actor_context
from leapp.models import (SystemFacts, CheckResult, SELinux, SelinuxPermissiveDecision,
                          SelinuxRelabelDecision)

# import needed just to be able to create valid model, but not important for test
from leapp.models import FirewallStatus, Firewalls


# FIXME: fix the file properly regarding the fix of the issue:
# # https://github.com/oamg/leapp-repository/issues/20
def create_selinux(static_mode, enabled, policy='targeted', mls_enabled=True):
    runtime_mode = static_mode if static_mode != 'disabled' else None

    return SELinux(
            runtime_mode=runtime_mode,
            static_mode=static_mode,
            enabled=enabled,
            policy=policy,
            mls_enabled=mls_enabled,
        )


def create_sysfacts(selinux):
    return SystemFacts(
            sysctl_variables=[],
            kernel_modules=[],
            users=[],
            groups=[],
            repositories=[],
            selinux=selinux,
            firewalls=Firewalls(
                firewalld=FirewallStatus(enabled=True, active=True),
                iptables=FirewallStatus(enabled=True, active=True),
            ),
        )


def test_actor_schedule_relabelling(current_actor_context):
    options = [create_selinux(static_mode='permissive', enabled=True),
               create_selinux(static_mode='enforcing', enabled=True)]

    for option in options:
        current_actor_context.feed(create_sysfacts(selinux=option))
        current_actor_context.run()
        assert current_actor_context.consume(CheckResult)
        assert current_actor_context.consume(SelinuxRelabelDecision)[0].set_relabel


def test_actor_set_permissive(current_actor_context):
    relabel = create_selinux(static_mode='enforcing', enabled=True)

    current_actor_context.feed(create_sysfacts(selinux=relabel))
    current_actor_context.run()
    assert current_actor_context.consume(CheckResult)
    assert current_actor_context.consume(SelinuxPermissiveDecision)[0].set_permissive


def test_actor_selinux_disabled(current_actor_context):
    disabled = create_selinux(enabled=False, static_mode='disabled')

    current_actor_context.feed(create_sysfacts(selinux=disabled))
    current_actor_context.run()
    assert not current_actor_context.consume(SelinuxRelabelDecision)
    assert not current_actor_context.consume(SelinuxPermissiveDecision)
