from leapp.actors import Actor
from leapp.models import TargetInitramfsTasks
from leapp.tags import IPUWorkflowTag, TargetTransactionChecksPhaseTag


class TMPActorToSatisfySanityChecks(Actor):
    """
    The actor does NOTHING but satisfy static sanity checks

    The actor is supposed to be removed in future once we resolve issue with
    sanity tests. See https://github.com/oamg/leapp/pull/680 for more details
    about the problems.
    """

    name = 'tmp_actor_to_satisfy_sanity_checks'
    consumes = ()
    produces = (TargetInitramfsTasks,)
    tags = (TargetTransactionChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        return
