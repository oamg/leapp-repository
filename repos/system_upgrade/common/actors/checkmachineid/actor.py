from leapp.actors import Actor
from leapp.libraries.actor import checkmachineid
from leapp.models import MachineIdInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckMachineId(Actor):
    """
    Check that /etc/machine-id contains a valid machine ID.

    The /etc/machine-id file must contain exactly 32 lowercase hexadecimal
    characters followed by a newline (33 bytes total). If the file is missing
    or contains an invalid ID, the system is in an unsupported state and the
    upgrade is inhibited.
    """

    name = 'check_machine_id'
    consumes = (MachineIdInfo,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checkmachineid.process()
