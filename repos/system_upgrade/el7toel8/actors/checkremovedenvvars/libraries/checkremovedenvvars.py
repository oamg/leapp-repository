from leapp.libraries.common.config import get_all_envs
from leapp.reporting import create_report
from leapp import reporting

DEPRECATED_VARS = ['LEAPP_GRUB_DEVICE']


def process():

    vars_to_report = []

    for var in get_all_envs():
        if var.name in DEPRECATED_VARS:
            vars_to_report.append(var.name)

    if vars_to_report:
        vars_str = ' '.join(vars_to_report)
        create_report([
            reporting.Title('Leapp detected removed environment variable usage'),
            reporting.Summary('The following Leapp related environment variable was removed: ' + vars_str),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Remediation(hint='Please do not use the reported variables'),
            reporting.Groups([reporting.Groups.UPGRADE_PROCESS, reporting.Groups.INHIBITOR]),
        ])
