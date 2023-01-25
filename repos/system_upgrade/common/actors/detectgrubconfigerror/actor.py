from leapp import reporting
from leapp.actors import Actor
from leapp.models import GrubConfigError
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


def _create_grub_error_report(error, title, summary, severity=reporting.Severity.LOW,
                              remediation=None, is_inhibitor=False):
    """
    A helper that produces a specific grub error report
    """
    # set default group for a grub error report
    groups = [reporting.Groups.BOOT]
    # set an inhibitor group
    if is_inhibitor:
        groups.append(reporting.Groups.INHIBITOR)
    report_fields = [reporting.Title(title),
                     reporting.Summary(summary),
                     reporting.Severity(severity),
                     reporting.Groups(groups)]
    if remediation:
        report_fields.append(remediation)
    # add information about grub config files
    report_fields.extend([reporting.RelatedResource('file', config_file) for config_file in error.files])
    # finally produce a report
    create_report(report_fields)


class DetectGrubConfigError(Actor):
    """
    Check grub configuration for various errors.

    Currently 3 types of errors are detected:
    - Syntax error in GRUB_CMDLINE_LINUX value;
    - Missing newline at the end of file;
    - Grubenv config file has a 1K size and doesn't end with a line feed.

    There should be only one message of each error type. If for any reason there are more - only the first error of
    each type is reported.
    """

    name = 'detect_grub_config_error'
    consumes = (GrubConfigError,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        # syntax error in GRUB_CMDLINE_LINUX, recoverable
        for error in [err for err in self.consume(GrubConfigError)
                      if err.error_type == GrubConfigError.ERROR_GRUB_CMDLINE_LINUX_SYNTAX]:
            _create_grub_error_report(
                    error=error,
                    title='Syntax error detected in grub configuration',
                    summary=('Syntax error was detected in GRUB_CMDLINE_LINUX value of grub configuration. '
                             'This error is causing booting and other issues. '
                             'Error is automatically fixed by add_upgrade_boot_entry actor.'),
                )
            break
        # missing newline, recoverable
        for error in [err for err in self.consume(GrubConfigError)
                      if err.error_type == GrubConfigError.ERROR_MISSING_NEWLINE]:
            _create_grub_error_report(
                    error=error,
                    title='Detected a missing newline at the end of grub configuration file',
                    summary=('The missing newline in /etc/default/grub causes booting issues when appending '
                             'new entries to this file during the upgrade. Leapp will automatically fix this '
                             'problem by appending the missing newline to the grub configuration file.')
                )
            break
        # corrupted configuration, inhibitor
        for error in [err for err in self.consume(GrubConfigError)
                      if err.error_type == GrubConfigError.ERROR_CORRUPTED_GRUBENV]:
            _create_grub_error_report(
                    error=error,
                    title='Detected a corrupted grubenv file',
                    summary=('The grubenv file must be valid to pass the upgrade correctly: \n'
                             '- an exact size of 1024 bytes is expected \n'
                             '- it cannot end with a newline. \n'
                             'The corruption could be caused by a manual modification of the file which '
                             'is not recommended.'),
                    severity=reporting.Severity.HIGH,
                    is_inhibitor=True,
                    remediation=reporting.Remediation(
                        hint='Delete {} file(s) and regenerate grubenv using the grub2-mkconfig tool'.format(
                            ','.join(error.files))))
            break
