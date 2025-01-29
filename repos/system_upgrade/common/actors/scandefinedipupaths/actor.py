from leapp.actors import Actor
from leapp.libraries.actor import scandefinedipupaths
from leapp.models import IPUPaths
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanDefinedIPUPaths(Actor):
    """
    Load defined IPU paths for the current major source system version
    and defined upgrade flavour.

    The upgrade paths are defined inside `files/upgrade_paths.json`.
    Based on the defined upgrade flavour (default, saphana, ..) loads particular
    definitions and filter out all upgrade paths from other system major versions.
    I.e. for RHEL 8.10 system with the default upgrade flavour, load all upgrade
    paths from any RHEL 8 system defined under the 'default' flavour.

    The code is mostly taken from the CLI command_utils. The duplicate solution
    is not so problematic now as it will be unified next time.

    Note the deprecation suppression is expected here as this is considered as
    temporary solution now.
    """

    name = 'scan_defined_ipu_paths'
    consumes = ()
    produces = (IPUPaths,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scandefinedipupaths.process()
