from leapp import reporting
from leapp.libraries.common.gpg import is_nogpgcheck_set
from leapp.libraries.common.rpms import get_installed_rpms
from leapp.libraries.stdlib import api
from leapp.models import TrustedGpgKeys

FMT_LIST_SEPARATOR = '\n    - '


def _get_installed_fps_tuple():
    """
    Return list of tuples (fingerprint, packager).
    """
    installed_fps_tuple = []
    rpms = get_installed_rpms()
    for rpm in rpms:
        rpm = rpm.strip()
        if not rpm:
            continue
        try:
            # NOTE: pgpsig is (none) for 'gpg-pubkey' entries
            name, version, dummy_release, dummy_epoch, packager, dummy_arch, dummy_pgpsig = rpm.split('|')
        except ValueError as e:
            # NOTE: it's seatbelt, but if it happens, seeing loong list of errors
            # will let us know earlier that we missed something really
            api.current_logger().error('Cannot perform the check of installed GPG keys after the upgrade.')
            api.current_logger().error('Cannot parse rpm output: {}'.format(e))
            continue
        if name != 'gpg-pubkey':
            continue
        installed_fps_tuple.append((version, packager))
    return installed_fps_tuple


def _report_cannot_check_keys(installed_fps):
    # NOTE: in this case, it's expected there will be always some GPG keys present
    summary = (
        'Cannot perform the check of GPG keys installed in the RPM DB'
        ' due to missing facts (TrustedGpgKeys) supposed to be generated'
        ' in the start of the upgrade process on the original system.'
        ' Unexpected unexpected installed GPG keys could be e.g. a mark of'
        ' a malicious attempt to hijack the upgrade process.'
        ' The list of all GPG keys in RPM DB:{sep}{key_list}'
        .format(
            sep=FMT_LIST_SEPARATOR,
            key_list=FMT_LIST_SEPARATOR.join(installed_fps)
        )
    )
    hint = (
        'Verify the installed GPG keys are expected.'
    )
    groups = [
        reporting.Groups.POST,
        reporting.Groups.REPOSITORY,
        reporting.Groups.SECURITY
    ]
    reporting.create_report([
        reporting.Title('Cannot perform the check of installed GPG keys after the upgrade.'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups(groups),
        reporting.Remediation(hint=hint),
    ])


def _report_unexpected_keys(unexpected_fps):
    summary = (
        'The system contains unexpected GPG keys after upgrade.'
        ' This can be caused e.g. by a manual intervention'
        ' or by malicious attempt to hijack the upgrade process.'
        ' The unexpected keys are the following:'
        ' {sep}{key_list}'
        .format(
            sep=FMT_LIST_SEPARATOR,
            key_list=FMT_LIST_SEPARATOR.join(unexpected_fps)
        )
    )
    hint = (
        'Verify the installed GPG keys are expected.'
    )
    groups = [
        reporting.Groups.POST,
        reporting.Groups.REPOSITORY,
        reporting.Groups.SECURITY
    ]
    reporting.create_report([
        reporting.Title('Detected unexpected GPG keys after the upgrade.'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups(groups),
        reporting.Remediation(hint=hint),
    ])


def process():
    """
    Verify the system does not have any unexpected gpg keys installed

    If the --no-gpgcheck option is used, this is skipped as we can not
    guarantee that what was installed came from trusted source
    """

    if is_nogpgcheck_set():
        api.current_logger().warning('The --nogpgcheck option is used: Skipping the check of installed GPG keys.')
        return

    installed_fps_tuple = _get_installed_fps_tuple()

    try:
        trusted_gpg_keys = next(api.consume(TrustedGpgKeys))
    except StopIteration:
        # unexpected (bug) situation; keeping as seatbelt for the security aspect
        installed_fps = ['{fp}: {packager}'.format(fp=fp, packager=packager) for fp, packager in installed_fps_tuple]
        _report_cannot_check_keys(installed_fps)
        return

    trusted_fps = [key.fingerprint for key in trusted_gpg_keys.items]
    unexpected_fps = []
    for fp, packager in installed_fps_tuple:
        if fp not in trusted_fps:
            unexpected_fps.append('{fp}: {packager}'.format(fp=fp, packager=packager))

    if unexpected_fps:
        _report_unexpected_keys(unexpected_fps)
