import os

from leapp.actors import Actor
from leapp.models import OSReleaseFacts
from leapp.reporting import Report
from leapp.libraries.common.reporting import report_generic
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckOSRelease(Actor):
    """
    Check if a supported release version of system's OS is in use. If not, inhibit upgrade process.

    Based on OS release collected facts, this actor will compare current release with supported
    versions. If a problem is found an inhibition message will be generated. This check can be
    skipped by using LEAPP_SKIP_CHECK_OS_RELEASE environment variable.
    """

    name = 'check_os_release'
    consumes = (OSReleaseFacts,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        skip_check = os.getenv('LEAPP_SKIP_CHECK_OS_RELEASE')
        if skip_check:
            report_generic(
                title='Skipped OS release check',
                summary='OS release check skipped via LEAPP_SKIP_CHECK_OS_RELEASE env var.',
                severity='low'
            )
            return

        min_supported_version = {
            'rhel': '7.6'
        }

        for facts in self.consume(OSReleaseFacts):
            if facts.release_id not in min_supported_version.keys():
                report_generic(
                    title='Unsupported OS id',
                    summary='Supported OS ids for upgrade process: ' + ','.join(min_supported_version.keys()),
                    flags=['inhibitor']
                )
                return

            min_version = [int(x) for x in min_supported_version[facts.release_id].split('.')]
            os_version = [int(x) for x in facts.version_id.split('.')]

            for current, minimal in zip(os_version, min_version):
                if current > minimal:
                    break

                if current < minimal:
                    report_generic(
                        title='Unsupported OS version',
                        summary='Minimal supported OS version for upgrade process: {}'.format(
                            min_supported_version[facts.release_id]),
                        flags=['inhibitor']
                    )
                    return
