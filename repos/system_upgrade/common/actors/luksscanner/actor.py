from leapp.actors import Actor
from leapp.libraries.actor import luksscanner
from leapp.models import LuksDumps, StorageInfo
from leapp.reporting import Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class LuksScanner(Actor):
    """
    Provides data about active LUKS devices.

    Scans all block devices of 'crypt' type and attempts to run 'cryptsetup luksDump' on them.
    For every 'crypt' device a LuksDump model is produced. Furthermore, if there is any LUKS token
    of type clevis, the concrete subtype is determined using 'clevis luks list'.
    """

    name = 'luks_scanner'
    consumes = (StorageInfo,)
    produces = (Report, LuksDumps)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        self.produce(luksscanner.get_luks_dumps_model())
