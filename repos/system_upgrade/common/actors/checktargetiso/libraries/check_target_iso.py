import os

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import version
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import StorageInfo, TargetOSInstallationImage


def inhibit_if_not_valid_iso_file(iso):
    target_os = f'{DISTRO_REPORT_NAMES.target} {version.get_target_major_version()}'
    remediation_hint = (
        'Check whether the supplied target OS installation path points to a valid'
        f' {target_os} ISO image.'
    )

    if not os.path.exists(iso.path):
        reporting.create_report([
            reporting.Title('Provided target OS installation ISO does not exist.'),
            reporting.Summary(
                f'The supplied {target_os} ISO path \'{iso.path}\' does not point to an existing file.'
            ),
            reporting.Remediation(hint=remediation_hint),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY]),
            reporting.Key('e99b767d6b6623641ba06b5e9c7542ce4c69f35f'),
        ])
        return True

    try:
        # TODO(mhecko): Figure out whether we will keep this since the scan actor is mounting the ISO anyway
        file_cmd_output = run(['file', '--mime', iso.path])
    except CalledProcessError as err:
        raise StopActorExecutionError(
            message=f'Failed to check whether {iso.path} is an ISO file.',
            details={'details': f'{err}'},
        )

    if 'application/x-iso9660-image' not in file_cmd_output['stdout']:
        reporting.create_report([
            reporting.Title(
                'Provided target OS installation image is not a valid ISO.'
            ),
            reporting.Summary(
                f'The provided {target_os} installation image path \'{iso.path}\''
                ' does not point to a valid ISO image.'
            ),
            reporting.Remediation(hint=remediation_hint),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY]),
            reporting.Key('21bf7b8c7bf079baa038374ccbce66a8d6d7d775'),
        ])
        return True
    return False


def inhibit_if_failed_to_mount_iso(iso):
    if iso.was_mounted_successfully:
        return False

    title = 'Failed to mount the provided target OS installation image.'
    target_os = f'{DISTRO_REPORT_NAMES.target} {version.get_target_major_version()}'
    summary = f'The provided {target_os} installation image {iso.path} could not be mounted.'
    hint = f'Verify that the provided ISO is a valid {target_os} installation image'

    reporting.create_report([
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Remediation(hint=hint),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Groups([reporting.Groups.REPOSITORY]),
        reporting.Key('156b28ab6ae13ccc2f2dddb6bca243e73eba7c6b'),
    ])
    return True


def inhibit_if_wrong_iso_os_version(iso):
    # If the major version could not be determined, the iso.os_version will be an empty string
    if not iso.os_version:
        reporting.create_report([
            reporting.Title(
                'Failed to determine target OS provided by the supplied installation image.'
            ),
            reporting.Summary(
                'Could not determine what OS or OS version is provided by the supplied'
                f' installation image located at {iso.path}.'
            ),
            reporting.Remediation(
                hint=(
                    'Check that the supplied image is a valid installation image of the'
                    f' target OS and version for the upgrade - {DISTRO_REPORT_NAMES.target}'
                    f' {version.get_target_major_version()}.'
                )
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY]),
            reporting.Key('abfee8507fdb049fea07e4c29bc74a501780287d'),
        ])
        return

    iso_os_major_version = iso.os_version.split('.')[0]
    req_major_ver = version.get_target_major_version()
    if iso_os_major_version != req_major_ver:
        target_distro = DISTRO_REPORT_NAMES.target

        reporting.create_report([
            reporting.Title('The provided installation image provides invalid target OS version.'),
            reporting.Summary(
                f'The provided {target_distro} installation image provides {target_distro} {iso.os_version},'
                f' however, a {target_distro} {req_major_ver} image is required for the upgrade.'
            ),
            reporting.Remediation(
                hint=f'Check that the supplied image is a valid {target_distro} installation image.'
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY]),
            reporting.Key('e94ecfc02541adca3fa3c9703847425dde736afe'),
        ])


def inhibit_if_iso_not_located_on_persistent_partition(iso):
    # Check whether the filesystem that on which the ISO resides is mounted in a persistent fashion
    storage_info = next(api.consume(StorageInfo), None)
    if not storage_info:
        raise StopActorExecutionError('Actor did not receive any StorageInfo message.')

    # Assumes that the path has been already checked for validity, e.g., the ISO path points to a file
    iso_mountpoint = os.path.realpath(iso.path)
    while not os.path.ismount(iso_mountpoint):  # Guaranteed to terminate because we must reach / eventually
        iso_mountpoint = os.path.dirname(iso_mountpoint)

    is_iso_on_persistent_partition = False
    for fstab_entry in storage_info.fstab:
        if os.path.realpath(fstab_entry.fs_file) == iso_mountpoint:
            is_iso_on_persistent_partition = True
            break

    if not is_iso_on_persistent_partition:
        target_ver = version.get_target_major_version()
        title = 'The target OS installation image is not located on a persistently mounted partition'
        summary = (
            f'The provided {DISTRO_REPORT_NAMES.target} {target_ver} installation image {iso.path} is located'
            ' on a partition without an entry in /etc/fstab, causing the partition to be persistently mounted.'
        )
        hint = (
            'Move the installation image to a partition that is persistently mounted, or create an /etc/fstab'
            ' entry for the partition on which the installation image is located.'
        )

        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Remediation(hint=hint),
            reporting.RelatedResource('file', '/etc/fstab'),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY]),
            reporting.Key('d379897ee3c164576c022fe68c8a43e6c9236bf5'),
        ])


def inhibit_if_iso_does_not_contain_basic_repositories(iso):
    missing_basic_repoids = {'BaseOS', 'AppStream'}

    for custom_repo in iso.repositories:
        missing_basic_repoids.remove(custom_repo.repoid)
        if not missing_basic_repoids:
            break

    if missing_basic_repoids:
        target_os = f'{DISTRO_REPORT_NAMES.target} {version.get_target_major_version()}'
        title = 'Provided target OS installation ISO is missing fundamental repositories.'

        missing_repos = ','.join(missing_basic_repoids)
        suffix = ('y' if len(missing_basic_repoids) == 1 else 'ies')
        summary = (
            f'The supplied {target_os} installation ISO {iso.path} does not contain'
            f' {missing_repos} repositor{suffix}'
        )
        hint = f'Check whether the supplied ISO is a valid {target_os} installation image.'

        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Remediation(hint),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY]),
            reporting.Key('58fc6fc9530aabd7454d4b4a6381046cab60a189'),
        ])


def perform_target_iso_checks():
    requested_target_iso_msg_iter = api.consume(TargetOSInstallationImage)
    target_iso = next(requested_target_iso_msg_iter, None)

    if not target_iso:
        return

    if next(requested_target_iso_msg_iter, None):
        api.current_logger().warning('Received multiple msgs with target ISO to use.')

    # Cascade the inhibiting conditions so that we do not spam the user with inhibitors
    is_iso_invalid = inhibit_if_not_valid_iso_file(target_iso)
    if not is_iso_invalid:
        failed_to_mount_iso = inhibit_if_failed_to_mount_iso(target_iso)
        if not failed_to_mount_iso:
            inhibit_if_wrong_iso_os_version(target_iso)
            inhibit_if_iso_not_located_on_persistent_partition(target_iso)
            inhibit_if_iso_does_not_contain_basic_repositories(target_iso)
