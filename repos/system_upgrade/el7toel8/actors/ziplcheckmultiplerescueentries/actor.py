from leapp.actors import Actor
from leapp.libraries.actor.ziplcheckmultiplerescueentries import inhibit_if_multiple_zipl_rescue_entries_present
from leapp.models import SourceBootLoaderConfiguration
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.reporting import Report


class ZiplCheckMultipleRescueEntries(Actor):
    """
    Inhibits the upgrade process if there are more than one rescue entries in
    the zipl configuration.
    """

    name = 'zipl_check_multiple_rescue_entries'
    consumes = (SourceBootLoaderConfiguration,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        boot_loader_configuration = next(self.consume(SourceBootLoaderConfiguration))
        inhibit_if_multiple_zipl_rescue_entries_present(boot_loader_configuration)
