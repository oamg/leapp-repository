from leapp.actors import Actor
from leapp.libraries.actor.private_firewalldcollectusedobjectnames import read_config
from leapp.models import FirewalldUsedObjectNames
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class FirewalldCollectUsedObjectNames(Actor):
    """
    This actor reads firewalld's configuration and produces Model
    FirewalldUsedObjectNames.
    """

    name = 'firewalld_collect_used_object_names'
    consumes = ()
    produces = (FirewalldUsedObjectNames,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(read_config())
