from leapp.actors import Actor
from leapp.libraries.actor.private_firewalldcollectdirectconfig import read_config
from leapp.models import FirewalldDirectConfig
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class FirewalldCollectDirectConfig(Actor):
    """
    This actor reads firewalld's configuration and produces Model
    FirewalldDirectConfig.
    """

    name = 'firewalld_collect_direct_config'
    consumes = ()
    produces = (FirewalldDirectConfig,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(read_config())
