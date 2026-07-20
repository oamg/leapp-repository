from leapp.actors import Actor
from leapp.libraries.actor import vircscanner
from leapp.models import DistributionSignedRPM, VircConfig
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class VircScanner(Actor):
    """
    Scan /etc/virc for lines that need to be removed during RHEL 8 to 9 upgrade.

    Detects 'filetype plugin on' and 'let skip_defaults_vim=1' lines
    and produces a VircConfig message for the modifier actor.
    """

    name = 'virc_scanner'
    consumes = (DistributionSignedRPM,)
    produces = (VircConfig,)
    tags = (FactsPhaseTag, IPUWorkflowTag,)

    def process(self):
        vircscanner.process(self)
