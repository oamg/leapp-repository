from leapp.actors import Actor
from leapp.libraries.actor.scandnfpluginpath import scan_dnf_pluginpath
from leapp.models import DnfPluginPathDetected
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanDnfPluginPath(Actor):
    """
    Scans DNF configuration for custom pluginpath option.

    This actor collects information about whether the pluginpath option is configured in DNF configuration
    and produces a DnfPluginPathDetected message, containing the information.
    """

    name = 'scan_dnf_pluginpath'
    consumes = ()
    produces = (DnfPluginPathDetected,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        scan_dnf_pluginpath()
