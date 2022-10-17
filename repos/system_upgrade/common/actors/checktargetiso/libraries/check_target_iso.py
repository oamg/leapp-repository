import os

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import version
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import TargetOSInstallationImage


def inhibit_if_not_valid_iso_file(iso):
    inhibit_title = None
    target_os = 'RHEL {}'.format(version.get_target_major_version())
    if not os.path.exists(iso.path):
        inhibit_title = 'Provided {target_os} installation ISO does not exists.'.format(target_os=target_os)
        inhibit_summary_tpl = 'The supplied {target_os} ISO path \'{iso_path}\' does not point to an existing file.'
        inhibit_summary = inhibit_summary_tpl.format(target_os=target_os, iso_path=iso.path)
    else:
        try:
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


def inhibit_if_not_target_rhel_iso(iso):
    # TODO(mhecko): Not implementing this would likely result in crashes due to leapp being unable to find target
    # #             content. However, that is bad user experience, since the user has likely no idea what went really
    # #             wrong.
    pass


def inhibit_if_iso_not_located_on_persistent_partition(iso):
    # TODO(mhecko)
    pass


def perform_target_iso_checks():
    requested_target_iso_msg_iter = api.consume(TargetOSInstallationImage)
    target_iso = next(requested_target_iso_msg_iter, None)

    if not target_iso:
        return

    if next(requested_target_iso_msg_iter, None):
        api.current_logger().warn('Received multiple msgs with target ISO to use.')

    inhibit_if_not_valid_iso_file(target_iso)
    inhibit_if_not_target_rhel_iso(target_iso)
    inhibit_if_iso_not_located_on_persistent_partition(target_iso)
