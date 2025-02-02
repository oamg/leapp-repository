from leapp.actors import Actor
from leapp.libraries.actor.libdbcheck import report_installed_packages
from leapp.models import DistributionSignedRPM, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class LibdbCheck(Actor):
    """
    Actor checking for presence of libdb(Berkeley DB) installation.

    Provides user with information related to upgrading systems
    with libdb installed.
    """
    name = 'libdb_check'
    consumes = (DistributionSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        report_installed_packages()
