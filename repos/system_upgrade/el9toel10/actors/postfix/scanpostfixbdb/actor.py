from leapp.actors import Actor
from leapp.libraries.actor import scanpostfixbdb
from leapp.models import DistributionSignedRPM, PostfixBdbConfiguration
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanPostfixBdb(Actor):
    """
    Detect Postfix Berkeley DB (hash/btree) lookup tables.

    RHEL 10 removed Berkeley DB, so hash: and btree: maps used on RHEL 9 will
    not work after the upgrade. Collect the relevant configuration lines so a
    later check actor can warn the administrator.
    """

    name = 'scan_postfix_bdb'
    consumes = (DistributionSignedRPM,)
    produces = (PostfixBdbConfiguration,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(scanpostfixbdb.scan_postfix_configuration())
