from leapp.actors import Actor
from leapp.libraries.actor.checkyumpluginsenabled import check_required_dnf_plugins_enabled
from leapp.models import PkgManagerInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


# NOTE: the name is kept for backwards compatibility, even though this scans only DNF now
class CheckYumPluginsEnabled(Actor):
    """
    Checks that the required DNF plugins are enabled.
    """

    name = 'check_yum_plugins_enabled'
    consumes = (PkgManagerInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        pkg_manager_info = next(self.consume(PkgManagerInfo))
        check_required_dnf_plugins_enabled(pkg_manager_info)
