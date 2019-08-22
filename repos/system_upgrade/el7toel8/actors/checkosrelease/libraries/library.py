import os

from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import OSReleaseFacts


COMMON_REPORT_TAGS = [reporting.Tags.SANITY]

related = [reporting.RelatedResource('file', '/etc/os-release')]


def skip_check():
    """ Check if an environment variable was used to skip this actor """
    if os.getenv('LEAPP_SKIP_CHECK_OS_RELEASE'):
        reporting.create_report([
            reporting.Title('Skipped OS release check'),
            reporting.Summary('Source RHEL release check skipped via LEAPP_SKIP_CHECK_OS_RELEASE env var.'),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags(COMMON_REPORT_TAGS)
        ] + related)

        return True
    return False


def check_os_version(supported_version):
    """ Check OS version and inhibit upgrade if not the same as supported ones """
    if not isinstance(supported_version, dict):
        api.current_logger().warning('The supported version value is invalid.')
        raise StopActorExecution()

    facts_messages = api.consume(OSReleaseFacts)
    facts = next(facts_messages, None)
    if list(facts_messages):
        api.current_logger().warning('Unexpectedly received more than one OSReleaseFacts message.')
    if not facts:
        raise StopActorExecutionError(
            'Could not check OS version', details={'details': 'No OSReleaseFacts facts found.'}
        )

    if facts.release_id not in supported_version:
        reporting.create_report([
            reporting.Title('Unsupported OS'),
            reporting.Summary('Only RHEL is supported by the upgrade process'),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags(COMMON_REPORT_TAGS),
            reporting.Flags([reporting.Flags.INHIBITOR])
        ] + related)

        return

    if not isinstance(supported_version[facts.release_id], list):
        raise StopActorExecutionError(
            'Invalid versions',
            details={'details': 'OS versions are invalid, please provide a valid list.'},
        )

    if facts.version_id not in supported_version[facts.release_id]:
        reporting.create_report([
            reporting.Title('Unsupported OS version'),
            reporting.Summary(
                'The supported OS versions for the upgrade process: {}'.format(
                    ', '.join(supported_version[facts.release_id])
                )
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags(COMMON_REPORT_TAGS),
            reporting.Flags([reporting.Flags.INHIBITOR])
        ] + related)
