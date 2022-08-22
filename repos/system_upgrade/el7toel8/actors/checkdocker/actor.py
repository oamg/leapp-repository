from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.common.rpms import has_package
from leapp.models import InstalledRPM
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckDocker(Actor):
    """
    Checks if Docker is installed and warns about its deprecation in RHEL8.
    """

    name = 'check_docker'
    consumes = (InstalledRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if has_package(InstalledRPM, 'docker'):
            create_report([
                reporting.Title('Transition from Docker to Podman in RHEL8'),
                reporting.Summary('Docker has been deprecated in favour of Podman in Red Hat Enterprise Linux 8. The '
                                  'docker package is going to be removed during the upgrade without migration of '
                                  'existing containers.'),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([reporting.Groups.TOOLS]),
                reporting.Remediation(hint='It is recommended to re-create the containers with the appropriate '
                                           'container images and reattach any in-use volumes using podman directly '
                                           'prior to the upgrade of the operating system, which should provide the '
                                           'same level of functionality. '),
                reporting.RelatedResource('package', 'docker'),
                reporting.ExternalLink(url='https://access.redhat.com/solutions/5213331',
                                       title='How do I migrate my Docker containers to Podman prior to moving from '
                                             'Red Hat Enterprise Linux 7 to Red Hat Enterprise Linux 8?')
            ])
