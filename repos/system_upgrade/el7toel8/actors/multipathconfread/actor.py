from leapp.actors import Actor
from leapp.libraries.actor import multipathconfread
from leapp.models import InstalledRedHatSignedRPM, MultipathConfFacts
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class MultipathConfRead(Actor):
    '''
    Reads multipath configuration files (multipath.conf, and any files in
    the multipath config directory) and extracts the necessary information
    '''

    name = 'multipath_conf_read'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (MultipathConfFacts,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        if multipathconfread.is_processable():
            res = multipathconfread.get_multipath_conf_facts()
            if res:
                self.produce(res)
