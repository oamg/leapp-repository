from leapp.actors import Actor
from leapp.libraries.actor.checkyumpluginsenabled import check_required_yum_plugins_enabled
from leapp.models import PkgManagerInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckYumPluginsEnabled(Actor):
    """
    Checks that the required yum plugins are enabled.
    """

    name = 'check_yum_plugins_enabled'
    consumes = (PkgManagerInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        pkg_manager_info = next(self.consume(PkgManagerInfo))
        check_required_yum_plugins_enabled(pkg_manager_info)
