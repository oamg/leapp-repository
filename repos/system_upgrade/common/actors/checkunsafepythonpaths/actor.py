from leapp.actors import Actor
from leapp.libraries.actor.checkunsafepythonpaths import perform_check
from leapp.models import UnsafePythonPaths
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckUnsafePythonPaths(Actor):
    """
    Inhibits the upgrade if third-party Python modules are detected in sys.path.

    This actor checks whether third-party Python modules (not from distribution-signed RPMs)
    are present in the target Python interpreter's sys.path. If such modules are detected,
    the upgrade is inhibited as they may interfere with the upgrade process or cause
    unexpected behavior after the upgrade.
    """

    name = 'check_unsafe_python_paths'
    consumes = (UnsafePythonPaths,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        perform_check()
