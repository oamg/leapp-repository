import rpm

from leapp import reporting
from leapp.libraries.common.gpg import GpgReadError, is_nogpgcheck_set, parse_gpg_key_from_ascii
from leapp.libraries.stdlib import api, format_list
from leapp.models import GpgKey, TrustedGpgKeys
from leapp.utils.deprecation import suppress_deprecation


def _get_installed_fps_tuple():
    """
    Get a list of tuples (fingerprint, packager).

    If some key fails to process it's return in a second separate list.
    If the rpm query fails the function returns None.

    :rtype: Optional[Tuple[List[Tuple[str, str]], List[str]]]
    """
    installed_fps_tuples = []
    failed_to_process = []
    try:
        ts = rpm.TransactionSet()
        matched = ts.dbMatch('name', 'gpg-pubkey')
    except rpm.error as err:
        api.current_logger().error('Cannot perform the check of installed GPG keys after the upgrade.')
        api.current_logger().error('Failed to run rpm query: {}'.format(err))
        return None

    for hdr in matched:
        try:
            # gpg-pubkey packages have the full ascii armor of a key in the DESCRIPTION tag
            key_infos = parse_gpg_key_from_ascii(hdr[rpm.RPMTAG_DESCRIPTION])
        except GpgReadError as err:
            api.current_logger().error('Cannot parse rpm output: {}'.format(err))
            failed_to_process.append(hdr[rpm.RPMTAG_NAME])
            continue

        if len(key_infos) != 1:
            name = hdr[rpm.RPMTAG_NAME]
            api.current_logger().error(
                'Expected one GPG key per gpg-pubkey, but parsed {} for {}, treating as a failed parse.'.format(
                    len(key_infos), name
                )
            )
            failed_to_process.append(name)
            continue

        installed_fps_tuples.append((key_infos[0].fingerprint, hdr[rpm.RPMTAG_PACKAGER]))
    return installed_fps_tuples, failed_to_process


def _report_cannot_check_query_failed():
    summary = (
        'Cannot verify GPG keys installed in the RPM DB due to failures while'
        ' querying the RPM DB.'
        ' Unexpected GPG keys may indicate an attempt to compromise the upgrade'
        ' process.'
    )
    hint = (
        'Verify the installed GPG keys are expected.'
    )
    groups = [
        reporting.Groups.POST,
        reporting.Groups.REPOSITORY,
        reporting.Groups.SECURITY,
    ]
    reporting.create_report([
        reporting.Title('Cannot perform the check of installed GPG keys after the upgrade.'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups(groups),
        reporting.Remediation(hint=hint),
    ])


def _report_cannot_check_parsing_failed():
    summary = (
        'Cannot verify GPG keys installed in the RPM DB due to failures during'
        ' parsing of the keys.'
        ' Unexpected GPG keys may indicate an attempt to compromise the upgrade'
        ' process.'
    )
    hint = (
        'Verify the installed GPG keys are expected.'
    )
    groups = [
        reporting.Groups.POST,
        reporting.Groups.REPOSITORY,
        reporting.Groups.SECURITY,
    ]
    reporting.create_report([
        reporting.Title('Cannot perform the check of installed GPG keys after the upgrade.'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups(groups),
        reporting.Remediation(hint=hint),
    ])


def _report_cannot_check_no_model(installed_fps):
    # NOTE: in this case, it's expected there will be always some GPG keys present
    summary = (
        'Cannot verify GPG keys installed in the RPM DB due to missing facts'
        ' (TrustedGpgKeys) which should have been generated at the start of'
        ' the upgrade process on the original system.'
        ' Unexpected GPG keys may indicate an attempt to compromise the upgrade'
        ' process. The list of all GPG keys in RPM DB:'
        f' {format_list(installed_fps, callback_sort=None)}'
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
        f'{format_list(unexpected_fps, callback_sort=None)}'
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


@suppress_deprecation(GpgKey)  # member of TrustedGpgKeys
def process():
    """
    Verify the system does not have any unexpected gpg keys installed

    If the --no-gpgcheck option is used, this is skipped as we can not
    guarantee that what was installed came from trusted source
    """

    if is_nogpgcheck_set():
        api.current_logger().warning('The --nogpgcheck option is used: Skipping the check of installed GPG keys.')
        return

    fps_result = _get_installed_fps_tuple()
    if fps_result is not None:
        installed_fps_tuple, failed_to_process = fps_result
        if failed_to_process:
            # even if just some keys failed to parse, ask for a complete
            # verification to be on the safe side
            _report_cannot_check_parsing_failed()
            return
    else:
        _report_cannot_check_query_failed()
        return

    try:
        trusted_gpg_keys = next(api.consume(TrustedGpgKeys))
    except StopIteration:
        # unexpected (bug) situation; keeping as seatbelt for the security aspect
        installed_fps = [f'{fp}: {packager}' for fp, packager in installed_fps_tuple]
        _report_cannot_check_no_model(installed_fps)
        return

    # NOTE(mmatuska): The deprecated TrustedGpgKeys.items is not processed here
    # anymore, it was documented as the contents of the rpmdb and trusted
    # directory, nothing more, and TrustedGpgKeys.keys now fulfills that
    # purpose
    trusted_fps = [key.fingerprint for key in trusted_gpg_keys.keys]
    unexpected_fps = []
    for fp, packager in installed_fps_tuple:
        if fp not in trusted_fps:
            unexpected_fps.append(f'{fp}: {packager}')

    if unexpected_fps:
        _report_unexpected_keys(unexpected_fps)
