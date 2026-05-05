from leapp.actors import Actor
from leapp.libraries.actor import multipathconfread
from leapp.models import DistributionSignedRPM, MultipathConfFacts8to9, MultipathInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class MultipathConfRead8to9(Actor):
    """
    Read multipath configuration files and extract the necessary information

    Related files:
      - /etc/multipath.conf
      - /etc/multipath/ - any files inside the directory
      - /etc/xdrdevices.conf

    Produces MultipathInfo with general information about multipath, and
    MultipathConfFacts8to9 with details needed for the 8 to 9 upgrade.
    """

    name = 'multipath_conf_read_8to9'
    consumes = (DistributionSignedRPM,)
    produces = (MultipathInfo, MultipathConfFacts8to9)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        multipathconfread.scan_and_emit_multipath_info()
