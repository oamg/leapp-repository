from leapp.actors import Actor
from leapp.libraries.common.reporting import report_generic
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckNmapFrontendActor(Actor):
    """
    Check if nmap-frontend is installed and
    report its inavalability in RHEL8
    """

    name = "nmap-frontend"
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def is_frontend_installed():
        for fact in self.consume(InstalledRedHatSignedRPM):
            for rpm in fact.items:
                if rpm.name == 'nmap-frontend':
                    return True
        return False

    def process(self):
        if is_frontend_installed():
            title = 'nmap-frontend has beed removed from RHEL 8'
            summary = 'Due to Python 2 deprecation nmap-frontend ' \
                      'package has been removed from RHEL8\n' \
                      'There is not replacement at the moment of writing.' \
                      'The package will be removed during upgrade process'
            severity = 'low'
            report_generic(title=title,
                           severity=severity,
                           summary=summary)
