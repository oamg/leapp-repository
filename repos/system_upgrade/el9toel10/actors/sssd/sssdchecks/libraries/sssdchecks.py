from leapp import reporting

FMT_LIST_SEPARATOR = '\n    - '


def check_config(model):
    if not model:
        return

    # If sss_ssh_knownhostsproxy was not configured, there is nothing to do
    if not model.ssh_config_files:
        return

    summary = (
        'SSSD\'s sss_ssh_knownhostsproxy tool is replaced by the more '
        'reliable sss_ssh_knownhosts tool. SSH\'s configuration will be updated '
        'to reflect this by updating every mention of sss_ssh_knownhostsproxy by '
        'the corresponding mention of sss_ssh_knownhosts, even those commented out.\n'
        'SSSD\'s ssh service will be enabled if not already done.\n'
        'The following files will be updated:{}{}'.format(
            FMT_LIST_SEPARATOR,
            FMT_LIST_SEPARATOR.join(model.sssd_config_files + model.ssh_config_files)
        )
    )

    report = [
        reporting.Title('The sss_ssh_knownhostsproxy will be replaced by sss_ssh_knownhosts'),
        reporting.Summary(summary),
        reporting.Groups([reporting.Groups.AUTHENTICATION, reporting.Groups.SECURITY]),
        reporting.Severity(reporting.Severity.INFO),
    ]

    reporting.create_report(report)
