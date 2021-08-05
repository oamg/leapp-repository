from leapp.actors import Actor
from leapp.libraries.actor.checkyumpluginsenabled import check_required_yum_plugins_enabled
from leapp.models import YumConfig
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckYumPluginsEnabled(Actor):
    """
    Checks that the required yum plugins are enabled.
    """

    name = 'check_yum_plugins_enabled'
    consumes = (YumConfig,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        yum_config = next(self.consume(YumConfig))
        check_required_yum_plugins_enabled(yum_config)
