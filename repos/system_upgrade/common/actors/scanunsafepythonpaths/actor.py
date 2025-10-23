from leapp.actors import Actor
from leapp.libraries.actor import scanunsafepythonpaths
from leapp.models import UnsafePythonPaths
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanUnsafePythonPaths(Actor):
    """
    Detect third-party Python modules installed in non-standard locations that may interfere with the upgrade process.

    Emit a high risk report if such directories exist, as they can introduce unexpected
    behavior during runtime or after reboot.
    """

    name = 'scan_unsafe_python_paths'
    consumes = ()
    produces = (UnsafePythonPaths,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        scanunsafepythonpaths.process()
