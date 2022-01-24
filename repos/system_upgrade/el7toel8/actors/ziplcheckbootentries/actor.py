from leapp.actors import Actor
from leapp.libraries.actor.ziplcheckbootentries import inhibit_if_invalid_zipl_configuration
from leapp.models import SourceBootLoaderConfiguration
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class ZiplCheckBootEntries(Actor):
    """
    Inhibits the upgrade if a problematic Zipl configuration is detected on the system.

    The configuration is considered problematic if it will cause troubles during its conversion to BLS.
    Such troubles can be caused by either containing multiple rescue entries, or containing rescue entries
    sharing the same kernel image version.
    """

    name = 'zipl_check_boot_entries'
    consumes = (SourceBootLoaderConfiguration,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        boot_loader_configuration = next(self.consume(SourceBootLoaderConfiguration))
        inhibit_if_invalid_zipl_configuration(boot_loader_configuration)
