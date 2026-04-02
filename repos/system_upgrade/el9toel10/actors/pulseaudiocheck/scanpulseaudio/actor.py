from leapp.actors import Actor
from leapp.libraries.actor.scanpulseaudio import scan_pulseaudio
from leapp.models import PulseAudioConfiguration
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanPulseAudio(Actor):
    """
    Scan the system for PulseAudio custom configuration.

    Detects whether PulseAudio is installed and checks for custom
    configuration that will not carry over to PipeWire after upgrade.
    """
    name = 'scan_pulseaudio'
    consumes = ()
    produces = (PulseAudioConfiguration,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(scan_pulseaudio())
