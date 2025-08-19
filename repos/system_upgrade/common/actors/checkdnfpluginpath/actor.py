from leapp.actors import Actor
from leapp.libraries.actor.checkdnfpluginpath import perform_check
from leapp.models import DnfPluginPathDetected
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckDnfPluginPath(Actor):
    """
    Inhibits the upgrade if a custom DNF plugin path is configured.

    This actor checks whether the pluginpath option is configured in /etc/dnf/dnf.conf and produces a report if it is.
    If the option is detected with any value, the upgrade is inhibited.
    """

    name = 'check_dnf_pluginpath'
    consumes = (DnfPluginPathDetected,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        perform_check()
