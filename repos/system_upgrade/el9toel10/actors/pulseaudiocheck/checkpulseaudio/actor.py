from leapp.actors import Actor
from leapp.libraries.actor.checkpulseaudio import check_pulseaudio
from leapp.models import DistributionSignedRPM, PulseAudioConfiguration, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckPulseAudio(Actor):
    """
    Check for custom PulseAudio configuration that won't carry over after upgrade.

    PulseAudio is replaced by PipeWire with the pipewire-pulseaudio compatibility
    plugin in RHEL 10. Custom PulseAudio configuration will not be applied.
    """
    name = 'check_pulseaudio'
    consumes = (DistributionSignedRPM, PulseAudioConfiguration)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        check_pulseaudio()
