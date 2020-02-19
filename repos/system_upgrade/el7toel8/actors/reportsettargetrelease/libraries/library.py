from leapp import reporting
from leapp.libraries.stdlib import api


def process():
    # TODO: skip if users are not using rhsm at all (RHELLEAPP-201)
    target_version = api.current_actor().configuration.version.target
    reporting.create_report([
        reporting.Title(
            'The subscription-manager release is going to be set after the upgrade'),
        reporting.Summary(
            'After the upgrade has completed the release of the subscription-manager will be set to {release}.'
            ' This will ensure that you will receive and keep the version you choose to upgrade to.'
            .format(release=target_version)
        ),
        reporting.Severity(reporting.Severity.LOW),
        reporting.Remediation(
            hint='If you wish to receive updates for the latest released version of RHEL 8, run `subscription-manager'
                 ' release --unset` after the upgrade.'),
        reporting.Tags([reporting.Tags.UPGRADE_PROCESS]),
        reporting.RelatedResource('package', 'subscription-manager')
    ])
