from leapp.actors import Actor
from leapp.libraries.actor.private_firewalldcollectglobalconfig import read_config
from leapp.models import FirewalldGlobalConfig
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class FirewalldCollectGlobalConfig(Actor):
    """
    This actor reads firewalld's configuration and produces Model
    FirewalldGlobalConfig.
    """

    name = 'firewalld_collect_global_config'
    consumes = ()
    produces = (FirewalldGlobalConfig,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(read_config())
