import os

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import SystemdBrokenSymlinksSource, SystemdServicesInfoSource

FMT_LIST_SEPARATOR = '\n    - '


def _report_broken_symlinks(symlinks):
    summary = (
        'Leapp detected broken systemd symlinks on the system that do not'
        ' correspond to any installed systemd unit.'
        ' This typically happens when the original systemd unit file has been'
        ' removed (e.g. an rpm removal) or renamed and the system configration'
        ' has not been properly modified.'
        ' These symlinks will not be handled during the in-place upgrade'
        ' as they are already broken.'
        ' The list of detected broken systemd symlinks:{}{}'
        .format(FMT_LIST_SEPARATOR, FMT_LIST_SEPARATOR.join(sorted(symlinks)))
    )

    command = ['/usr/bin/rm'] + symlinks

    hint = (
        'Remove the invalid symlinks before the upgrade.'
    )

    reporting.create_report([
        reporting.Title(
            'Detected broken systemd symlinks for non-existing services'
        ),
        reporting.Summary(summary),
        reporting.Remediation(hint=hint, commands=[command]),
        reporting.Severity(reporting.Severity.LOW),
        reporting.Groups([reporting.Groups.FILESYSTEM]),
    ])


def _report_enabled_services_broken_symlinks(symlinks):
    summary = (
        'Leapp detected broken systemd symlinks on the system that correspond'
        ' to existing systemd units, but on different paths. This could lead'
        ' in future to unexpected behaviour. Also, these symlinks will not be'
        ' handled during the in-place upgrade as they are already broken.'
        ' The list of detected broken symlinks:{}{}'
        .format(FMT_LIST_SEPARATOR, FMT_LIST_SEPARATOR.join(sorted(symlinks)))
    )

    hint = (
        'Fix the broken symlinks before the upgrade or remove them. For this'
        ' purpose, you can re-enable or disable the related systemd services'
        ' using the systemctl tool.'
    )

    reporting.create_report([
        reporting.Title(
            'Detected broken systemd symlinks for existing services'
        ),
        reporting.Summary(summary),
        reporting.Remediation(hint=hint),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.FILESYSTEM]),
    ])


def _is_enabled(unit, service_files):
    # FIXME(pstodulk): currently our msgs contain only information about systemd
    # services. If the unit (broken symlink) refers to timers, etc. They will
    # be treated now as disabled (read: symlink is broken and there is not
    # a corresponding unit-file on the system). Considering it for now as
    # minor issue that will be resolved in future.
    # NOTE: One of possible solution is to put the information about enabled broken
    # symlinks to the msg, so it can be just consumed.
    for service_file in service_files:
        if service_file.name == unit:
            return service_file.state == 'enabled'
    return False


def process():
    broken_symlinks_info = next(api.consume(SystemdBrokenSymlinksSource), None)
    if not broken_symlinks_info:
        # nothing to do
        return
    services = next(api.consume(SystemdServicesInfoSource), None)
    if not services:
        # This is just a seatbelt. It's not expected this msg will be missing.
        # Skipping tests.
        raise StopActorExecutionError('Missing SystemdServicesInfoSource message.')

    enabled_to_report = []
    to_report = []
    for broken_symlink in broken_symlinks_info.broken_symlinks:
        unit = os.path.basename(broken_symlink)
        if _is_enabled(unit, services.service_files):
            enabled_to_report.append(broken_symlink)
        else:
            to_report.append(broken_symlink)

    if enabled_to_report:
        _report_enabled_services_broken_symlinks(enabled_to_report)

    if to_report:
        _report_broken_symlinks(to_report)
