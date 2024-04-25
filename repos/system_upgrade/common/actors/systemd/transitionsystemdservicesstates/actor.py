from leapp.actors import Actor
from leapp.libraries.actor import transitionsystemdservicesstates
from leapp.models import (
    SystemdServicesInfoSource,
    SystemdServicesInfoTarget,
    SystemdServicesPresetInfoSource,
    SystemdServicesPresetInfoTarget,
    SystemdServicesTasks
)
from leapp.reporting import Report
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class TransitionSystemdServicesStates(Actor):
    """
    Transition states of systemd services between source and target systems

    Services on the target system might end up in incorrect/unexpected state
    after an upgrade. This actor puts such services into correct/expected
    state.

    A SystemdServicesTasks message is produced containing all tasks that need
    to be executed to put all services into the correct states.

    The correct states are determined according to following rules:
        - All enabled services remain enabled
        - All masked services remain masked
        - Disabled services will be enabled if they are disabled by default on
          the source system (by preset files), but enabled by default on target
          system, otherwise they will remain disabled
        - Runtime enabled service (state == runtime-enabled) are treated
          the same as disabled services
        - Services in other states are not handled as they can't be
          enabled/disabled

    Two reports are generated:
        - Report with services that were corrected from disabled to enabled on
          the upgraded system
        - Report with services that were newly enabled on the upgraded system
          by a preset
    """

    name = 'transition_systemd_services_states'
    consumes = (
        SystemdServicesInfoSource,
        SystemdServicesInfoTarget,
        SystemdServicesPresetInfoSource,
        SystemdServicesPresetInfoTarget
    )
    produces = (Report, SystemdServicesTasks)
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        transitionsystemdservicesstates.process()
