from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.libraries.common import rhsm


def _report_set_release():
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
        reporting.Groups([reporting.Groups.UPGRADE_PROCESS]),
        reporting.RelatedResource('package', 'subscription-manager')
    ])


def _report_unhandled_release():
    # TODO: set the POST group after it's created.
    target_version = api.current_actor().configuration.version.target
    hint_command = 'subscription-manager release --set {}'.format(target_version)
    # FIXME: This should use Dialogs and Answers to offer post-upgrade remediation
    # so that users can choose whether to --set or --unset the release number
    hint = 'Set the new release (or unset it) after the upgrade using subscription-manager: ' + hint_command
    reporting.create_report([
        reporting.Title(
            'The subscription-manager release is going to be kept as it is during the upgrade'),
        reporting.Summary(
            'The upgrade is executed with the --no-rhsm option (or with'
            ' the LEAPP_NO_RHSM environment variable). In this case, the subscription-manager'
            ' will not be configured during the upgrade. If the system is subscribed and release'
            ' is set already, you could encounter issues to get RHEL 8 content using DNF/YUM'
            ' after the upgrade.'
        ),
        reporting.Severity(reporting.Severity.LOW),
        reporting.Remediation(hint=hint),
        reporting.Groups([reporting.Groups.UPGRADE_PROCESS]),
        reporting.RelatedResource('package', 'subscription-manager')
    ])


def process():
    if rhsm.skip_rhsm():
        _report_unhandled_release()
    else:
        _report_set_release()
