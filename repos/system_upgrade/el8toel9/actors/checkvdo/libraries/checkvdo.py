from leapp import reporting
from leapp.libraries.stdlib import api

_report_title = reporting.Title('VDO devices migration to LVM management')


def _create_unexpected_resuilt_report(devices):
    names = [x.name for x in devices]
    multiple = len(names) > 1
    summary = ['Unexpected result checking device{0}'.format('s' if multiple else '')]
    summary.extend([x.failure for x in devices])
    summary = '\n'.join(summary)

    remedy_hint = ''.join(('Resolve the conditions leading to the reported '
                           'failure{0} '.format('s' if multiple else ''),
                           'and re-run the upgrade.'))

    reporting.create_report([
        _report_title,
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.DRIVERS]),
        reporting.Remediation(hint=remedy_hint),
        reporting.Groups([reporting.Groups.INHIBITOR])
    ])


def _process_post_conversion_vdos(vdos):
    # Post-conversion VDOs that have definitively been shown to not have
    # completed the migration to LVM management generate an inhibiting report.
    post_conversion = [x for x in vdos if (not x.complete) and (not x.check_failed)]
    if post_conversion:
        devices = [x.name for x in post_conversion]
        multiple = len(devices) > 1
        summary = ''.join(('VDO device{0} \'{1}\' '.format('s' if multiple else '',
                                                           ', '.join(devices)),
                           'did not complete migration to LVM management. ',
                           'The named device{0} '.format('s' if multiple else ''),
                           '{0} successfully converted at the '.format('were' if multiple else 'was'),
                           'device format level; however, the expected LVM management '
                           'portion of the conversion did not take place. This '
                           'indicates that an exceptional condition (for example, a '
                           'system crash) likely occured during the conversion '
                           'process. The LVM portion of the conversion must be '
                           'performed in order for upgrade to proceed.'))

        remedy_hint = ('Consult the VDO to LVM conversion process '
                       'documentation for how to complete the conversion.')

        reporting.create_report([
            _report_title,
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.DRIVERS]),
            reporting.Remediation(hint=remedy_hint),
            reporting.Groups([reporting.Groups.INHIBITOR])
        ])

    # Post-conversion VDOs that were not successfully checked for having
    # completed the migration to LVM management.
    post_conversion = [x for x in vdos if (not x.complete) and x.check_failed]
    if post_conversion:
        _create_unexpected_resuilt_report(post_conversion)


def _process_pre_conversion_vdos(vdos):
    # Pre-conversion VDOs generate an inhibiting report.
    if vdos:
        devices = [x.name for x in vdos]
        multiple = len(devices) > 1
        summary = ''.join(('VDO device{0} \'{1}\' require{2} '.format('s' if multiple else '',
                                                                      ', '.join(devices),
                                                                      '' if multiple else 's'),
                           'migration to LVM management.'
                           'After performing the upgrade VDO devices can only be '
                           'managed via LVM. Any VDO device not currently managed '
                           'by LVM must be converted to LVM management before '
                           'upgrading. The data on any VDO device not converted to '
                           'LVM management will be inaccessible after upgrading.'))

        remedy_hint = ('Consult the VDO to LVM conversion process '
                       'documentation for how to perform the conversion.')

        reporting.create_report([
            _report_title,
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.DRIVERS]),
            reporting.Remediation(hint=remedy_hint),
            reporting.Groups([reporting.Groups.INHIBITOR])
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

    checked = [x for x in devices if x.check_failed]
    if checked:
        _create_unexpected_resuilt_report(checked)

    unchecked = [x for x in devices if not x.check_failed]
    if unchecked:
        no_vdo_devices = api.current_actor().get_no_vdo_devices_response()
        if no_vdo_devices:
            summary = ('User has asserted there are no VDO devices on the '
                       'system in need of conversion to LVM management.')

            reporting.create_report([
                _report_title,
                reporting.Summary(summary),
                reporting.Severity(reporting.Severity.INFO),
                reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.DRIVERS]),
                reporting.Groups([])
            ])
        elif no_vdo_devices is False:
            summary = ('User has opted to inhibit upgrade in regard to '
                       'potential VDO devices requiring conversion to LVM '
                       'management.')
            remedy_hint = ('Install the \'vdo\' package and re-run upgrade to '
                           'check for VDO devices requiring conversion.')

            reporting.create_report([
                _report_title,
                reporting.Summary(summary),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.DRIVERS]),
                reporting.Remediation(hint=remedy_hint),
                reporting.Groups([reporting.Groups.INHIBITOR])
            ])


def check_vdo(conversion_info):
    _process_pre_conversion_vdos(conversion_info.pre_conversion)
    _process_post_conversion_vdos(conversion_info.post_conversion)
    _process_undetermined_conversion_devices(conversion_info.undetermined_conversion)
