from leapp import reporting

_report_title = reporting.Title('VDO devices migration to lvm-based management')

def check_vdo(conversion_info):
    for pre_conversion in conversion_info.pre_conversion_vdos:
        reporting.create_report([
            _report_title,
            reporting.Summary(
                "VDO device '{0}' requires migration".format(
                    pre_conversion.name)),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SERVICES, reporting.Tags.DRIVERS]),
            reporting.Remediation(hint = 'Perform VDO to LVM migration for the VDO device.'),
            reporting.Flags([reporting.Flags.INHIBITOR])
        ])

    for post_conversion in conversion_info.post_conversion_vdos:
        if not post_conversion.complete:
            reporting.create_report([
                _report_title,
                reporting.Summary(
                    "VDO device '{0}' did not complete migration".format(
                    post_conversion.name)),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Tags([reporting.Tags.SERVICES, reporting.Tags.DRIVERS]),
                reporting.Remediation(
                    hint = 'Complete VDO to LVM migration for the VDO device.'),
                reporting.Flags([reporting.Flags.INHIBITOR])
            ])
