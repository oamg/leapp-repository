from leapp import reporting
from leapp.actors import Actor
from leapp.models import FirewalldUsedObjectNames
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class FirewalldCheckServiceTftpClient(Actor):
    """
    This actor will inhibit if firewalld's configuration is using service
    'tftp-client'.
    """

    name = 'firewalld_check_service_tftp_client'
    consumes = (FirewalldUsedObjectNames,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        tftp_client_service = 'tftp-client'
        send_report = False

        for facts in self.consume(FirewalldUsedObjectNames):
            if tftp_client_service in facts.services:
                send_report = True

        if send_report:
            create_report([
                reporting.Title('Firewalld Service tftp-client Is Unsupported'),
                reporting.Summary('Firewalld has service "{service}" enabled. '
                                  'Service "{service}" has been removed in RHEL-9.'.format(
                                      service=tftp_client_service)),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([reporting.Groups.SANITY, reporting.Groups.FIREWALL]),
                reporting.Groups([reporting.Groups.INHIBITOR]),
                reporting.Remediation(
                    hint=(
                        'Remove all usage of service "{service}" from '
                        'firewalld\'s permanent configuration. '
                        'It may be in use by: zones, policies, or rich rules.\n'
                        'Usage can be found by listing zone and policy '
                        'configuration:\n'
                        '  # firewall-cmd --permanent --list-all-zones\n'
                        '  # firewall-cmd --permanent --list-all-policies\n'
                        'Example to remove usage from a zone:\n'
                        '  # firewall-cmd --permanent --zone public '
                        ' --remove-service {service}\n'.format(
                            service=tftp_client_service)
                        )
                    ),
            ])
