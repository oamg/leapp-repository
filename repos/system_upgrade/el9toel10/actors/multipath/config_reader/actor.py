from leapp.actors import Actor
from leapp.libraries.actor import multipathconfread
from leapp.models import DistributionSignedRPM, MultipathConfFacts9to10, MultipathInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class MultipathConfRead9to10(Actor):
    """
    Read multipath configuration files and extract the necessary information

    Related files:
      - /etc/multipath.conf
      - /etc/multipath/ - any files inside the directory

    Produces MultipathInfo with general information about multipath, and
    MultipathConfFacts9to10 with details needed for the 9 to 10 upgrade.
    """

    name = 'multipath_conf_read_9to10'
    consumes = (DistributionSignedRPM,)
    produces = (MultipathInfo, MultipathConfFacts9to10)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        multipathconfread.scan_and_emit_multipath_info()
