from leapp import reporting


def check_config(model):
    if not model:
        return

    # If sss_ssh_knownhostsproxy was not configured, there is nothing to do
    if not model.ssh_config_files:
        return

    summary = (
        'SSSD\'s sss_ssh_knownhostsproxy tool is replaced by the more '
        'reliable sss_ssh_knownhosts tool. SSH\'s configuration will be updated '
        'to reflect this by updating every mention of sss_ssh_knownhostsproxy '
        'by the corresponding mention of sss_ssh_knownhosts.\n'
        'SSSD\'s ssh service will be enabled if not already done.'
    )

    report = [
        reporting.Title('sss_ssh_knownhosts replaces sss_ssh_knownhostsproxy.'),
        reporting.Summary(summary),
        reporting.Groups([reporting.Groups.AUTHENTICATION, reporting.Groups.SECURITY]),
        reporting.Severity(reporting.Severity.INFO),
    ]

    for file in model.sssd_config_files + model.ssh_config_files:
        report.append(reporting.RelatedResource('file', file))

    reporting.create_report(report)
