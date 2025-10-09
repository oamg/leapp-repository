from leapp.actors import Actor
from leapp.libraries.actor import checkunsafepythonpaths
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckUnsafePythonPaths(Actor):
    """
    Detect third-party Python modules installed in non-standard locations that may interfere with the upgrade process.

    Emit a high risk report if such directories exist, as they can introduce unexpected
    behavior during runtime or after reboot.
    """

    name = 'check_unsafe_python_paths'
    consumes = ()
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkunsafepythonpaths.process()
