from leapp.actors import Actor
from leapp.libraries.actor.checkmultiplepackageversions import check
from leapp.models import InstalledRPM
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag


class CheckMultiplePackageVersions(Actor):
    """
    Check for problematic 32bit packages installed together with 64bit ones.

    If a known problematic 32bit package is found, the upgrade will be inhibited with the detailed
    report how to solve the problem if such a remedy exists.
    """

    name = 'multiple_package_versions'
    consumes = (InstalledRPM,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        check()
