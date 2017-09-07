from leapp.snactor.fixture import current_actor_context
from leapp.models import CheckResult, FirewallDecisionM


def test_actor_execution_choice_n(current_actor_context):
    current_actor_context.feed(FirewallDecisionM(disable_choice='N'))
    current_actor_context.run()
    assert not current_actor_context.consume(CheckResult)


def test_actor_execution_choice_s(current_actor_context):
    current_actor_context.feed(FirewallDecisionM(disable_choice='S'))
    current_actor_context.run()
    assert not current_actor_context.consume(CheckResult)
