from leapp.actors import Actor
from leapp.libraries.actor.checkthirdpartytargetpythonmodules import perform_check
from leapp.models import ThirdPartyTargetPythonModules
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckThirdPartyTargetPythonModules(Actor):
    """
    Produces a report if any third-party target Python modules are detected on the source system.

    If such modules are detected, a high risk report is produced.
    """

    name = 'check_third_party_target_python_modules'
    consumes = (ThirdPartyTargetPythonModules,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        perform_check()
