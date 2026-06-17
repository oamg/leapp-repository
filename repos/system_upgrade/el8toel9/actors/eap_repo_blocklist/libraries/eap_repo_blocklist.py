from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RepositoriesBlacklisted

EAP_RHEL9_REPOS = {
    '7.4': 'jb-eap-7.4-for-rhel-9-x86_64-rpms',
    '8.0': 'jb-eap-8.0-for-rhel-9-x86_64-rpms',
    '8.1': 'jb-eap-8.1-for-rhel-9-x86_64-rpms',
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

    to_blocklist = [
        repo for version, repo in EAP_RHEL9_REPOS.items()
        if version != installed_eap
    ]

    api.current_logger().info('Blocklisting repos: {}'.format(to_blocklist))
    api.produce(RepositoriesBlacklisted(repoids=to_blocklist))
