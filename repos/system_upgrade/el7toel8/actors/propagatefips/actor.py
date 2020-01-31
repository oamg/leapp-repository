from leapp.actors import Actor
from leapp.models import FIPSFacts, KernelCmdlineArg
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class PropagateFIPS(Actor):
    """
    Preserve FIPS mode as it was before the upgrade.
    """

    name = 'propagate_fips'
    consumes = (FIPSFacts,)
    produces = (KernelCmdlineArg,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        for fact in self.consume(FIPSFacts):
            self.log.info(repr(fact))
        if fact.enabled:
            self.produce(KernelCmdlineArg(**{'key': 'fips', 'value': '1'}))
            self.produce(KernelCmdlineArg(**{'key': 'FIPSTRACE', 'value': '1'}))
