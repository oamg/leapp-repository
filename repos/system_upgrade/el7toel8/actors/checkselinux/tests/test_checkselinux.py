from leapp.snactor.fixture import current_actor_context
from leapp.models import (SystemFacts, CheckResult, SELinux, SelinuxPermissiveDecision,
                          SelinuxRelabelDecision)


def test_actor_schedule_relabelling(current_actor_context):
    options = [SELinux(static_mode='permissive', enabled=True),
              SELinux(static_mode='enforcing', enabled=True)]

    for option in options:
        current_actor_context.feed(SystemFacts(selinux=option))
        current_actor_context.run()
        assert current_actor_context.consume(CheckResult)
        assert current_actor_context.consume(SelinuxRelabelDecision)[0].set_relabel


def test_actor_set_permissive(current_actor_context):
    relabel = SELinux(static_mode='enforcing', enabled=True)

    current_actor_context.feed(SystemFacts(selinux=relabel))
    current_actor_context.run()
    assert current_actor_context.consume(CheckResult)
    assert current_actor_context.consume(SelinuxPermissiveDecision)[0].set_permissive


def test_actor_selinux_disabled(current_actor_context):
    disabled = SELinux(enabled=False)

    current_actor_context.feed(SystemFacts(selinux=disabled))
    current_actor_context.run()
    assert not current_actor_context.consume(SelinuxRelabelDecision)
    assert not current_actor_context.consume(SelinuxPermissiveDecision)
