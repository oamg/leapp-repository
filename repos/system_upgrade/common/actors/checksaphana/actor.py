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
    - If the major target release is 8, and this system is _NOT_ running on x86_64, the upgrade is inhibited.
    - If the major target release is 9, and this system is _NOT_ running on x86_64 or ppc64le,
      the upgrade is inhibited.
    - If SAP HANA 1 has been detected on the system the upgrade is inhibited since there is no supported upgrade path
      with installed SAP HANA 1.
    - If SAP HANA 2 has been detected, the upgrade will be inhibited if an unsupported version for the target release
      has been detected (<8.8, <9.2).
    - If the target release >=8.8 or >=9.2, the upgrade will be inhibited unless a user confirms to proceed
      for the currently installed SAP HANA 2.0 version and the chosen target release.
    - If SAP HANA is running the upgrade is inhibited.
    """

    name = 'check_sap_hana'
    consumes = (SapHanaInfo,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        perform_check()
