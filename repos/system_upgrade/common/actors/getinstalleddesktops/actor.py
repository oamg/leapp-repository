from leapp.actors import Actor
from leapp.libraries.actor.getinstalleddesktops import get_installed_desktops
from leapp.models import InstalledDesktopsFacts, InstalledRPM
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class GetInstalledDesktops(Actor):
    """
    Actor checks if kde or gnome desktop environments
    are installed and what desktop is default.
    """

    name = 'get_installed_desktops'
    consumes = (InstalledRPM,)
    produces = (InstalledDesktopsFacts,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        facts = get_installed_desktops()
        self.produce(InstalledDesktopsFacts(
            gnome_installed=facts["gnome_installed"],
            kde_installed=facts["kde_installed"]))
