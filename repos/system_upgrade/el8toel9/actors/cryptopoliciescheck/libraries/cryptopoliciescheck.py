from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import CopyFile, TargetUserSpacePreupgradeTasks


def _get_files_to_copy(cpi):
    return [f.path for f in cpi.custom_policies + cpi.custom_modules]


def process(cpi_messages):
    cpi = next(cpi_messages, None)
    if list(cpi_messages):
        api.current_logger().warning('Unexpectedly received more than one CryptoPolicyInfo message.')
    if not cpi:
        raise StopActorExecutionError(
            'Could not check crypto policies status',
            details={'details': 'No CryptoPolicyInfo facts found.'}
        )

    if cpi.current_policy != 'DEFAULT':
        # If we have to change the crypto policies inside the target userspace container,
        # we need update-crypto-policies script inside as well as potential custom policies files
        files = [CopyFile(src=f) for f in _get_files_to_copy(cpi)]
        api.produce(TargetUserSpacePreupgradeTasks(install_rpms=['crypto-policies-scripts'],
                                                   copy_files=files))

        # When non-default crypto policy is used, it might be outdated. Recommend user to revisit.
        # exceptions are here the FIPS and FUTURE policies, which are more future-proof.
        if cpi.current_policy in ('FIPS', 'FUTURE'):
            return
        reporting.create_report([
            reporting.Title('System-wide crypto policy is set to non-DEFAULT policy'),
            reporting.Summary((
                    "The system-wide crypto policies are set to `{}` value. This might be"
                    " outdated decision, the custom crypto policy might be outdated and no"
                    " longer meeting the security standards. Please, review the current crypto"
                    " policies settings. If this is intentional and up-to-date, you can ignore"
                    " this message. The custom crypto policy will be configured on the updated"
                    " system."
                ).format(cpi.current_policy)),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([reporting.Groups.SECURITY, reporting.Groups.SANITY]),
            reporting.Remediation(hint="Review the current policy in /etc/crypto-policies/state/CURRENT.pol"),
            reporting.RelatedResource('package', 'crypto-policies'),
            reporting.ExternalLink(
                url='https://red.ht/rhel-9-security-considerations',
                title='Security Considerations in adopting RHEL 9'
            )
        ])
