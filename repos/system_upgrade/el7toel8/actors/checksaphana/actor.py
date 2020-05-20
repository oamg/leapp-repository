from leapp.actors import Actor
from leapp.libraries.actor.checksaphana import perform_check
from leapp.models import SapHanaInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckSapHana(Actor):
    """
    If SAP HANA has been detected, several checks are performed to ensure a successful upgrade.

    If the upgrade flavour is 'default' no checks are being executed.

    The following checks are executed:
    - If this system is _NOT_ running on x86_64, the upgrade is inhibited.
    - If SAP HANA 1 has been detected on the system the upgrade is inhibited since it is not supported on RHEL8.
    - If SAP HANA 2 has been detected, the upgrade will be inhibited if an unsupported version for the target release
      has been detected.
    - If SAP HANA is running the upgrade is inhibited.
    """

    name = 'check_sap_hana'
    consumes = (SapHanaInfo,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        perform_check()
