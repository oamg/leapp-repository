import os

from leapp import reporting


def check_config(model):
    if not model:
        return

    # If sss_ssh_knownhostsproxy was not configured, there is nothing to do
    if len(model.ssh_config_files) == 0:
        return

    unwritable = []
    for file in model.sssd_config_files + model.ssh_config_files:
        if not os.access(file, os.W_OK, effective_ids=True):
            unwritable.append(file)

    summary = 'SSSD\'s sss_ssh_knownhostsproxy tool is replaced by the more ' \
    'reliable sss_ssh_knownhosts tool. SSH\'s configuration will be updated ' \
    'to reflect this.\n' \
    'SSSD\'s ssh service needs to be enabled.'
    if len(unwritable) > 0:
        summary += '\nThe following files are not writable: ' + ', '.join(unwritable)

    report = [
        reporting.Title('sss_ssh_knownhosts replaces sss_ssh_knownhostsproxy.'),
        reporting.Summary(summary),
        reporting.Groups([reporting.Groups.AUTHENTICATION, reporting.Groups.SECURITY]),
        reporting.Severity(reporting.Severity.INFO),
    ]

    if len(unwritable) > 0:
        report.append(reporting.Remediation(hint='Correct the unwritable files permissions.'))

    for file in model.sssd_config_files + model.ssh_config_files:
        report.append(reporting.RelatedResource('file', file))

    reporting.create_report(report)
