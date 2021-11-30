from leapp.actors import Actor
from leapp.libraries.actor.checkkdeapps import get_kde_apps_info
from leapp.models import InstalledKdeAppsFacts, InstalledRPM
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class CheckKdeApps(Actor):
    """
    Actor checks which KDE apps are installed.
    """

    name = 'check_kde_apps'
    consumes = (InstalledRPM,)
    produces = (InstalledKdeAppsFacts,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        app_facts = get_kde_apps_info()
        self.produce(InstalledKdeAppsFacts(
            installed_apps=app_facts))
