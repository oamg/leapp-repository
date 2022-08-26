from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import SystemdServicesTasks

FMT_LIST_SEPARATOR = '\n    - '


def _inhibit_upgrade_with_conflicts(conflicts):
    summary = (
        'The requested states for systemd services on the target system are in conflict.'
        ' The following systemd services were requested to be both enabled and'
        ' disabled on the target system:{}{}'
        .format(FMT_LIST_SEPARATOR, FMT_LIST_SEPARATOR.join(sorted(conflicts)))
    )
    report = [
        reporting.Title('Conflicting requirements of systemd service states'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.SANITY]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
    ]
    reporting.create_report(report)


def check_conflicts():
    services_to_enable = set()
    services_to_disable = set()
    for task in api.consume(SystemdServicesTasks):
        services_to_enable.update(task.to_enable)
        services_to_disable.update(task.to_disable)

    conflicts = services_to_enable.intersection(services_to_disable)
    if conflicts:
        _inhibit_upgrade_with_conflicts(conflicts)
