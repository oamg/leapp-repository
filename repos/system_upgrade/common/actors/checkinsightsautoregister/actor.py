from leapp.actors import Actor
from leapp.libraries.actor import checkinsightsautoregister
from leapp.models import InstalledRPM, RpmTransactionTasks
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckInsightsAutoregister(Actor):
    """
    Checks if system can be automatically registered into Red Hat Insights

    The registration is skipped if NO_INSIGHTS_REGISTER=1 environment variable
    is set, the --no-insights-register command line argument present. if the
    system isn't registered with subscription-manager.

    Additionally, the insights-client package is required. If it's missing an
    RpmTransactionTasks is produced to install it during the upgrade.

    A report is produced informing about the automatic registration and
    eventual insights-client package installation.
    """

    name = 'check_insights_auto_register'
    consumes = (InstalledRPM,)
    produces = (Report, RpmTransactionTasks)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkinsightsautoregister.process()
