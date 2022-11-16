import os

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import version
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import StorageInfo, TargetOSInstallationImage


def inhibit_if_not_valid_iso_file(iso):
    inhibit_title = None
    target_os = 'RHEL {}'.format(version.get_target_major_version())
    if not os.path.exists(iso.path):
        inhibit_title = 'Provided {target_os} installation ISO does not exists.'.format(target_os=target_os)
        inhibit_summary_tpl = 'The supplied {target_os} ISO path \'{iso_path}\' does not point to an existing file.'
        inhibit_summary = inhibit_summary_tpl.format(target_os=target_os, iso_path=iso.path)
    else:
        try:
            # TODO(mhecko): Figure out whether we will keep this since the scan actor is mounting the ISO anyway
            file_cmd_output = run(['file', '--mime', iso.path])
            if 'application/x-iso9660-image' not in file_cmd_output['stdout']:
                inhibit_title = 'Provided {target_os} installation image is not a valid ISO.'.format(
                        target_os=target_os)
                summary_tpl = ('The provided {target_os} installation image path \'{iso_path}\''
                               'does not point to a valid ISO image.')
                inhibit_summary = summary_tpl.format(target_os=target_os, iso_path=iso.path)

        except CalledProcessError as err:
            raise StopActorExecutionError(message='Failed to check whether {0} is an ISO file.'.format(iso.path),
                                          details={'details': '{}'.format(err)})
    if inhibit_title:
        remediation_hint = ('Check whether the supplied target OS installation path points to a valid'
                            '{target_os} ISO image.'.format(target_os=target_os))

        reporting.create_report([
            reporting.Title(inhibit_title),
            reporting.Summary(inhibit_summary),
            reporting.Remediation(hint=remediation_hint),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY]),
        ])
        return True
    return False


def inhibit_if_failed_to_mount_iso(iso):
    if iso.was_mounted_successfully:
        return False

    target_os = 'RHEL {0}'.format(version.get_target_major_version())
    title = 'Failed to mount the provided {target_os} installation image.'
    summary = 'The provided {target_os} installation image {iso_path} could not be mounted.'
    hint = 'Verify that the provided ISO is a valid {target_os} installation image'
    reporting.create_report([
        reporting.Title(title.format(target_os=target_os)),
        reporting.Summary(summary.format(target_os=target_os, iso_path=iso.path)),
        reporting.Remediation(hint=hint.format(target_os=target_os)),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Groups([reporting.Groups.REPOSITORY]),
    ])
    return True


def inhibit_if_wrong_iso_rhel_version(iso):
    # If the major version could not be determined, the iso.rhel_version will be an empty string
    if not iso.rhel_version:
        reporting.create_report([
            reporting.Title(
                'Failed to determine RHEL version provided by the supplied installation image.'),
            reporting.Summary(
                'Could not determine what RHEL version does the supplied installation image'
                ' located at {iso_path} provide.'.format(iso_path=iso.path)
            ),
            reporting.Remediation(hint='Check that the supplied image is a valid RHEL installation image.'),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY]),
        ])
        return

    iso_rhel_major_version = iso.rhel_version.split('.')[0]
    req_major_ver = version.get_target_major_version()
    if iso_rhel_major_version != req_major_ver:
        summary = ('The provided RHEL installation image provides RHEL {iso_rhel_ver}, however, a RHEL '
                   '{required_rhel_ver} image is required for the upgrade.')

        reporting.create_report([
            reporting.Title('The provided installation image provides invalid RHEL version.'),
            reporting.Summary(summary.format(iso_rhel_ver=iso.rhel_version, required_rhel_ver=req_major_ver)),
            reporting.Remediation(hint='Check that the supplied image is a valid RHEL installation image.'),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY]),
        ])


def inhibit_if_iso_not_located_on_persistent_partition(iso):
    # Check whether the filesystem that on which the ISO resides is mounted in a persistent fashion
    storage_info = next(api.consume(StorageInfo), None)
    if not storage_info:
        raise StopActorExecutionError('Actor did not receive any StorageInfo message.')

    # Assumes that the path has been already checked for validity, e.g., the ISO path points to a file
    iso_mountpoint = iso.path
    while not os.path.ismount(iso_mountpoint):  # Guaranteed to terminate because we must reach / eventually
        iso_mountpoint = os.path.dirname(iso_mountpoint)

    is_iso_on_persistent_partition = False
    for fstab_entry in storage_info.fstab:
        if fstab_entry.fs_file == iso_mountpoint:
            is_iso_on_persistent_partition = True
            break

    if not is_iso_on_persistent_partition:
        target_ver = version.get_target_major_version()
        title = 'The RHEL {target_ver} installation image is not located on a persistently mounted partition'
        summary = ('The provided RHEL {target_ver} installation image {iso_path} is located'
                   ' on a partition without an entry in /etc/fstab, causing the partition '
                   ' to be persistently mounted.')
        hint = ('Move the installation image to a partition that is persistently mounted, or create an /etc/fstab'
                ' entry for the partition on which the installation image is located.')

        reporting.create_report([
            reporting.Title(title.format(target_ver=target_ver)),
            reporting.Summary(summary.format(target_ver=target_ver, iso_path=iso.path)),
            reporting.Remediation(hint=hint),
            reporting.RelatedResource('file', '/etc/fstab'),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY]),
        ])


def inihibit_if_iso_does_not_contain_basic_repositories(iso):
    missing_basic_repoids = {'BaseOS', 'AppStream'}

    for custom_repo in iso.repositories:
        missing_basic_repoids.remove(custom_repo.repoid)
        if not missing_basic_repoids:
            break

    if missing_basic_repoids:
        target_ver = version.get_target_major_version()

        title = 'Provided RHEL {target_ver} installation ISO is missing fundamental repositories.'
        summary = ('The supplied RHEL {target_ver} installation ISO {iso_path} does not contain '
                   '{missing_repos} repositor{suffix}')
        hint = 'Check whether the supplied ISO is a valid RHEL {target_ver} installation image.'

        reporting.create_report([
            reporting.Title(title.format(target_ver=target_ver)),
            reporting.Summary(summary.format(target_ver=target_ver,
                                             iso_path=iso.path,
                                             missing_repos=','.join(missing_basic_repoids),
                                             suffix=('y' if len(missing_basic_repoids) == 1 else 'ies'))),
            reporting.Remediation(hint=hint.format(target_ver=target_ver)),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.REPOSITORY]),
        ])


def perform_target_iso_checks():
    requested_target_iso_msg_iter = api.consume(TargetOSInstallationImage)
    target_iso = next(requested_target_iso_msg_iter, None)

    if not target_iso:
        return

    if next(requested_target_iso_msg_iter, None):
        api.current_logger().warn('Received multiple msgs with target ISO to use.')

    # Cascade the inhibiting conditions so that we do not spam the user with inhibitors
    is_iso_invalid = inhibit_if_not_valid_iso_file(target_iso)
    if not is_iso_invalid:
        failed_to_mount_iso = inhibit_if_failed_to_mount_iso(target_iso)
        if not failed_to_mount_iso:
            inhibit_if_wrong_iso_rhel_version(target_iso)
            inhibit_if_iso_not_located_on_persistent_partition(target_iso)
            inihibit_if_iso_does_not_contain_basic_repositories(target_iso)
