from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RepositoriesSetupTasks
from leapp.reporting import create_report, Title, Summary, Severity, Groups, Remediation

EAP_RHEL9_REPOS = {
    '7.4': [
        'jb-eap-7.4-for-rhel-9-x86_64-rpms',
        'jb-eap-7.4-els-for-rhel-9-x86_64-rpms',
    ],
    '8.0': [
        'jb-eap-8.0-for-rhel-9-x86_64-rpms',
    ],
    '8.1': [
        'jb-eap-8.1-for-rhel-9-x86_64-rpms',
    ],
}


def process():
    installed_eap = None

    for rpm_msg in api.consume(DistributionSignedRPM):
        for rpm in rpm_msg.items:
            if rpm.name == 'eap7-wildfly':
                installed_eap = '7.4'
                break
            elif rpm.name == 'eap8-wildfly':
                if '8.0.' in rpm.version:
                    installed_eap = '8.0'
                elif '8.1.' in rpm.version:
                    installed_eap = '8.1'
                break

    if not installed_eap:
        api.current_logger().info('No EAP installation detected, skipping repo blocklist')
        return

    api.current_logger().info('Detected installed EAP version: {}'.format(installed_eap))

    if installed_eap == '8.0':
        create_report([
            Title('JBoss EAP 8.0 upgrade via leapp is not supported'),
            Summary(
                'JBoss EAP 8.0 is not in the leapp upgrade scope. '
                'Upgrade JBoss EAP to 8.1 before performing the RHEL upgrade.'
            ),
            Severity(Severity.HIGH),
            Groups([Groups.INHIBITOR]),
            Remediation(hint='Upgrade JBoss EAP to version 8.1 prior to running leapp upgrade.'),
        ])
        return

    to_enable = EAP_RHEL9_REPOS[installed_eap]
    to_blocklist = [
        repo
        for version, repos in EAP_RHEL9_REPOS.items()
        if version != installed_eap
        for repo in repos
    ]

    api.current_logger().info('Enabling repos: {}'.format(to_enable))
    api.current_logger().info('Blocking repos: {}'.format(to_blocklist))
    api.produce(RepositoriesSetupTasks(to_enable=to_enable, to_block=to_blocklist))