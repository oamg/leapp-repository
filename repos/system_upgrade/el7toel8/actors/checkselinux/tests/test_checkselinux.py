from leapp.snactor.fixture import current_actor_context
from leapp.models import (Report, SELinuxFacts, SelinuxPermissiveDecision,
                          SelinuxRelabelDecision)


# FIXME: fix the file properly regarding the fix of the issue:
# # https://github.com/oamg/leapp-repository/issues/20
def create_selinuxfacts(static_mode, enabled, policy='targeted', mls_enabled=True):
    runtime_mode = static_mode if static_mode != 'disabled' else None

    return SELinuxFacts(
        runtime_mode=runtime_mode,
        static_mode=static_mode,
        enabled=enabled,
        policy=policy,
        mls_enabled=mls_enabled
    )


def test_actor_schedule_relabelling(current_actor_context):
    facts = [create_selinuxfacts(static_mode='permissive', enabled=True),
             create_selinuxfacts(static_mode='enforcing', enabled=True)]

    for fact in facts:
        current_actor_context.feed(fact)
        current_actor_context.run()
        assert current_actor_context.consume(Report)
        assert current_actor_context.consume(SelinuxRelabelDecision)[0].set_relabel


def test_actor_set_permissive(current_actor_context):
    relabel = create_selinuxfacts(static_mode='enforcing', enabled=True)

    current_actor_context.feed(relabel)
    current_actor_context.run()
    assert current_actor_context.consume(Report)
    assert current_actor_context.consume(SelinuxPermissiveDecision)[0].set_permissive


def test_actor_selinux_disabled(current_actor_context):
    disabled = create_selinuxfacts(enabled=False, static_mode='disabled')

    current_actor_context.feed(disabled)
    current_actor_context.run()
    assert not current_actor_context.consume(SelinuxRelabelDecision)
    assert not current_actor_context.consume(SelinuxPermissiveDecision)
