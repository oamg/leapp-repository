from leapp.actors import Actor
from leapp.libraries.actor import rocescanner
from leapp.models import RoceDetected
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RoCEScanner(Actor):
    """
    Detect active RoCE NICs on IBM Z machines.

    Detect whether RoCE is configured on the system and produce
    the RoceDetected message with active RoCE NICs - if any exists.
    The active connections are scanned using NetworkManager (`nmcli`) as
    RoCE is supposed to be configured via NetworkManager since
    RHEL 8; see:
        https://www.ibm.com/docs/en/linux-on-systems?topic=guide-add-additional-roce-interface

    The scan is performed only on IBM Z machines.
    """

    name = 'roce_scanner'
    consumes = ()
    produces = (RoceDetected,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        rocescanner.process()
