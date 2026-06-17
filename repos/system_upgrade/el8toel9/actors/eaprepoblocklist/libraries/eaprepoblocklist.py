from leapp.libraries.common.config import get_source_distro_id, get_target_distro_id
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RepositoriesSetupTasks
from leapp.reporting import create_report, Groups, Remediation, Severity, Summary, Title

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


def detect_installed_eap():
    for rpm_msg in api.consume(DistributionSignedRPM):
        for rpm in rpm_msg.items:
            if rpm.name == 'eap7-wildfly':
                return '7.4'
            if rpm.name == 'eap8-wildfly':
                if '8.0.' in rpm.version:
                    return '8.0'
                if '8.1.' in rpm.version:
                    return '8.1'
                # This is hypothetical, it cannot happen, but if so, let's at least create a log
                api.current_logger().warning('Detected unexpected EAP version: %s', rpm.version)
    return None


def process():
    if get_source_distro_id() != 'rhel' or get_target_distro_id() != 'rhel':
        api.current_logger().info('Skipping EAP repo check - not a RHEL to RHEL upgrade')
        return

    installed_eap = detect_installed_eap()

    if not installed_eap:
        api.current_logger().info('No EAP installation detected, skipping repo blocklist')
        return

    api.current_logger().info('Detected installed EAP version: {}'.format(installed_eap))

    if installed_eap == '8.0':
        create_report([
            Title('JBoss EAP 8.0 upgrade via leapp is not supported'),
            Summary(
                'JBoss EAP 8.0 is not in the leapp upgrade scope. '
                'Upgrade JBoss EAP to 8.1 before performing the upgrade.'
            ),
            Severity(Severity.HIGH),
            Groups([Groups.INHIBITOR]),
            Remediation(hint='Upgrade JBoss EAP to version 8.1 prior to running leapp upgrade.'),
        ])
        return

    to_enable = EAP_RHEL9_REPOS[installed_eap]
    to_block = [
        repo
        for version, repos in EAP_RHEL9_REPOS.items()
        if version != installed_eap
        for repo in repos
    ]

    api.current_logger().debug('Enabling repos: {}'.format(to_enable))
    api.current_logger().debug('Blocking repos: {}'.format(to_block))
    api.produce(RepositoriesSetupTasks(to_enable=to_enable, to_block=to_block))
