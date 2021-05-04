from leapp.actors import Actor
from leapp.libraries.actor.scansaphana import perform_sap_hana_scan
from leapp.models import SapHanaInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanSapHana(Actor):
    """
    Gathers information related to SAP HANA instances on the system.

    This actor collects information from SAP HANA installations and produces a message containing the details.
    The actor will determine whether SAP HANA is installed, running and which version is present on the system.
    """

    name = 'scan_sap_hana'
    consumes = ()
    produces = (SapHanaInfo,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        perform_sap_hana_scan()
