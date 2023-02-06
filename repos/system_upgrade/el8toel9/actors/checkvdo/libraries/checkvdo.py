from leapp import reporting
from leapp.libraries.stdlib import api

VDO_DOC_URL = 'https://red.ht/import-existing-vdo-volumes-to-lvm'


def _report_skip_check():
    if not api.current_actor().get_vdo_answer():
        return

    summary = ('User has asserted all VDO devices on the system have been '
               'successfully converted to LVM management or no VDO '
               'devices are present.')
    reporting.create_report([
        reporting.Title('Skipping the VDO check of block devices'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.DRIVERS]),
    ])


def _process_failed_check_devices(conversion_info):
    # Post-conversion VDOs that were not successfully checked for having
    # completed the migration to LVM management.
    # Return True if failed checks detected
    devices = [x for x in conversion_info.post_conversion if (not x.complete) and x.check_failed]
    devices += [x for x in conversion_info.undetermined_conversion if x.check_failed]
    if not devices:
        return False

    if api.current_actor().get_vdo_answer():
        # User asserted all possible VDO should be already converted - skip
        return True

    names = [x.name for x in devices]
    multiple = len(names) > 1
    summary = ['Unexpected result checking device{0}'.format('s' if multiple else '')]
    summary.extend([x.failure for x in devices])
    summary = '\n'.join(summary)

    remedy_hint = ''.join(('Resolve the conditions leading to the reported '
                           'failure{0} '.format('s' if multiple else ''),
                           'and re-run the upgrade.'))

    reporting.create_report([
        reporting.Title('Checking VDO conversion to LVM management of block devices failed'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.DRIVERS]),
        reporting.Remediation(hint=remedy_hint),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.ExternalLink(url=VDO_DOC_URL, title='Importing existing VDO volumes to LVM')
    ])
    return True


def _process_post_conversion_vdos(vdos):
    # Post-conversion VDOs that have definitively been shown to not have
    # completed the migration to LVM management generate an inhibiting report.
    post_conversion = [x for x in vdos if (not x.complete) and (not x.check_failed)]
    if post_conversion:
        devices = [x.name for x in post_conversion]
        multiple = len(devices) > 1
        summary = (
            'VDO device{s_suffix} \'{devices_str}\' '
            'did not complete migration to LVM management. '
            'The named device{s_suffix} {was_were} successfully converted '
            'at the device format level; however, the expected LVM management '
            'portion of the conversion did not take place. This indicates '
            'that an exceptional condition (for example, a system crash) '
            'likely occurred during the conversion process. The LVM portion '
            'of the conversion must be performed in order for upgrade '
            'to proceed.'
            .format(
                s_suffix='s' if multiple else '',
                devices_str=', '.join(devices),
                was_were='were' if multiple else 'was',
            )
        )

        remedy_hint = ('Consult the VDO to LVM conversion process '
                       'documentation for how to complete the conversion.')

        reporting.create_report([
            reporting.Title('Detected VDO devices that have not finished the conversion to LVM management.'),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.DRIVERS]),
            reporting.Remediation(hint=remedy_hint),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.ExternalLink(url=VDO_DOC_URL, title='Importing existing VDO volumes to LVM')
        ])


def _process_pre_conversion_vdos(vdos):
    # Pre-conversion VDOs generate an inhibiting report.
    if vdos:
        devices = [x.name for x in vdos]
        multiple = len(devices) > 1
        summary = (
            'VDO device{s_suffix} \'{devices_str}\' require{s_suffix_verb} '
            'migration to LVM management.'
            'After performing the upgrade VDO devices can only be '
            'managed via LVM. Any VDO device not currently managed '
            'by LVM must be converted to LVM management before '
            'upgrading. The data on any VDO device not converted to '
            'LVM management will be inaccessible after upgrading.'
            .format(
                s_suffix='s' if multiple else '',
                s_suffix_verb='' if multiple else 's',
                devices_str=', '.join(devices),
            )
        )

        remedy_hint = ('Consult the VDO to LVM conversion process '
                       'documentation for how to perform the conversion.')

        reporting.create_report([
            reporting.Title('Detected VDO devices not managed by LVM'),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.DRIVERS]),
            reporting.Remediation(hint=remedy_hint),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.ExternalLink(url=VDO_DOC_URL, title='Importing existing VDO volumes to LVM')
        ])


def _process_undetermined_conversion_devices(devices):
    # Practically we cannot have both unchecked and checked (with failure)
    # devices.  Devices are only unchecked if the vdo package is not installed
    # on the system and can only be checked with failure if it is.  Only in the
    # case of a bug could there be both.
    #
    # We process the two possibilities serially knowing that only one, if any,
    # could occur, but that if somehow both do (a bug) we're at least made
    # aware that it happened.
    #
    # A device can only end up as undetermined either via a check that failed
    # or if it was not checked.  If the info for the device indicates that it
    # did not have a check failure that means it was not checked.
    # Return True if failed checks detected

    unchecked = [x for x in devices if not x.check_failed]
    if not unchecked:
        return False

    if api.current_actor().get_vdo_answer():
        # User asserted no VDO devices are present
        return True

    summary = (
        'The check of block devices could not be performed as the \'vdo\' '
        'package is not installed. All VDO devices must be converted to '
        'LVM management prior to the upgrade to prevent the loss of data.')
    remedy_hint = ('Install the \'vdo\' package and re-run upgrade to '
                   'check for VDO devices requiring conversion or confirm '
                   'that all VDO devices, if any, are managed by LVM.')

    reporting.create_report([
        reporting.Title('Cannot perform the VDO check of block devices'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.DRIVERS]),
        reporting.Remediation(hint=remedy_hint),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.ExternalLink(url=VDO_DOC_URL, title='Importing existing VDO volumes to LVM')
    ])
    return True


def check_vdo(conversion_info):
    _process_pre_conversion_vdos(conversion_info.pre_conversion)
    _process_post_conversion_vdos(conversion_info.post_conversion)

    detected_under_dev = _process_undetermined_conversion_devices(conversion_info.undetermined_conversion)
    detected_failed_check = _process_failed_check_devices(conversion_info)
    if detected_under_dev or detected_failed_check:
        _report_skip_check()
