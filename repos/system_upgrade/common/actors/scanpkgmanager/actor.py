from leapp.actors import Actor
from leapp.libraries.actor import scanpkgmanager
from leapp.models import PkgManagerInfo
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class ScanPkgManager(Actor):
    """
    Provides data about package manager (yum/dnf)
    """

    name = 'scan_pkg_manager'
    consumes = ()
    produces = (PkgManagerInfo,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scanpkgmanager.process()
