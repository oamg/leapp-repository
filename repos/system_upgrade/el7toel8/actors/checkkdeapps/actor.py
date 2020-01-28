from leapp.actors import Actor
from leapp.tags import FactsPhaseTag, IPUWorkflowTag
from leapp.models import InstalledKdeAppsFacts, InstalledRPM
from leapp.libraries.actor.library import get_kde_apps_info


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
