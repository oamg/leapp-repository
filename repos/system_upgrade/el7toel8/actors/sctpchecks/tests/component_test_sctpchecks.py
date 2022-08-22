from leapp.actors import Actor
from leapp.models import RpmTransactionTasks, SCTPConfig
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


def test_sctp_wanted(current_actor_context):
    current_actor_context.feed(SCTPConfig(wanted=True))
    current_actor_context.run()
    assert current_actor_context.consume(RpmTransactionTasks)
    assert current_actor_context.consume(RpmTransactionTasks)[0].to_install == ['kernel-modules-extra']


def test_sctp_empty_config(current_actor_context):
    current_actor_context.feed(SCTPConfig())
    current_actor_context.run()
    assert not current_actor_context.consume(RpmTransactionTasks)


def test_sctp_no_config(current_actor_context):
    current_actor_context.run()
    assert not current_actor_context.consume(RpmTransactionTasks)


def test_sctp_unwanted(current_actor_context):
    current_actor_context.feed(SCTPConfig(wanted=False))
    current_actor_context.run()
    assert not current_actor_context.consume(RpmTransactionTasks)
