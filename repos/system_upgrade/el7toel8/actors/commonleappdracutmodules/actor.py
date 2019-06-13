from leapp.actors import Actor
from leapp.libraries.actor import modscan
from leapp.models import RequiredUpgradeInitramPackages, UpgradeDracutModule
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class CommonLeappDracutModules(Actor):
    """
    Influences the generation of the initram disk

    The initram disk generation is influenced by specifying necessary dracut modules and packages that are
    required to be installed in the target userspace so required fields can be included.
    Modules to be added are specified via the UpgradeDracutModule message.
    Packages to install on the target userspace are specified by the RequiredUpgradeInitramPackages message.
    """

    name = 'common_leapp_dracut_modules'
    consumes = ()
    produces = (RequiredUpgradeInitramPackages, UpgradeDracutModule)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        modscan.process()
