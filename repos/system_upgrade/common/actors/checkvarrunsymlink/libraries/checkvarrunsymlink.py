from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import TrackedFilesInfoSource

VAR_RUN_PATH = '/var/run'


def _get_real_path(tracked_files):
    for finfo in tracked_files.files:
        if finfo.path == VAR_RUN_PATH:
            return finfo.real_path
    return None


def process():
    tracked_files = next(api.consume(TrackedFilesInfoSource), None)
    if not tracked_files:
        api.current_logger().warning(
            'The TrackedFilesInfoSource message is missing. Skipping the check of /var/run symlink.'
        )
        return

    real_path = _get_real_path(tracked_files)
    if real_path is None or real_path == '/run':
        return

    reporting.create_report([
        reporting.Title('/var/run is not correctly configured'),
        reporting.Summary(
            'In modern Linux systems that use systemd, /run is a tmpfs filesystem'
            ' managed by systemd and /var/run must be a symbolic link pointing to'
            ' ../run for compatibility. The current system does not have /var/run'
            ' configured as expected. This can cause boot failures, service startup'
            ' failures, or login issues both on the current system and after an'
            ' in-place upgrade.'
        ),
        reporting.Remediation(
            hint=(
                'Back up current /var/run directory if needed and replace it by'
                ' symbolic link pointing to "../run".'
            ),
            commands=[
                ['bash', '-c', 'mv /var/run /tmp/var_run.bak && ln -s ../run /var/run'],
            ]
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.FILESYSTEM, reporting.Groups.INHIBITOR]),
        reporting.RelatedResource('directory', VAR_RUN_PATH),
    ])
