from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.common.rpms import has_package
from leapp.models import InstalledRedHatSignedRPM, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

UNSUPPORTED_VERSIONS = ['2.1', '3.0', '3.1', '5.0']


class DotnetUnsupportedVersionsCheck(Actor):
    """
    Check for installed .NET versions that are no longer supported.
    """

    name = 'dotnet_unsupported_versions_check'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        unsupported_versions_report_text = ''

        for unsupported_version in UNSUPPORTED_VERSIONS:
            runtime_package = f'dotnet-runtime-{unsupported_version}'
            if has_package(InstalledRedHatSignedRPM, runtime_package):
                unsupported_versions_report_text += '{0}{1}'.format('\n    - ', unsupported_version)

        if unsupported_versions_report_text:
            reporting.create_report([
                reporting.Title('Unsupported .NET versions installed on the system.'),
                reporting.Summary(
                    (
                        'The following versions of .NET are no longer supported :{0}\n'
                        'Applications that use these runtimes will no longer work\n'
                        'and must be updated to target a newer version of .NET.'
                    ).format(
                        unsupported_versions_report_text
                    )
                ),
                reporting.Severity(reporting.Severity.HIGH)])
