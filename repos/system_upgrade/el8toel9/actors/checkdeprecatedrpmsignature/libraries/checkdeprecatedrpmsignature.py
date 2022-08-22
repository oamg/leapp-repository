from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import CryptoPolicyInfo, InstalledRPM

FMT_LIST_SEPARATOR = '\n    - '

# FIXME(pstodulk): Adding the links to the summary as information inside has
# serious impact. This will create a duplication of links for Satellite and
# Cockpit UI when reading the report, but we need to be sure they are printed
# in the /var/log/leapp/leapp-report.txt file as well. Remove them when the
# framework prints external links in the file as well.
SUMMARY_FMT = (
    'Digital signatures using SHA-1 hash algorithm are no longer considered'
    ' secure and are not allowed to be used on RHEL 9 systems by default.'
    ' This causes issues when using DNF/RPM to handle packages with RSA/SHA1'
    ' signatures as the signature cannot be checked with the default'
    ' cryptographic policy. Any such packages cannot be installed, removed,'
    ' or replaced unless the signature check is disabled in dnf/rpm'
    ' or SHA-1 is enabled using non-default crypto-policies.'
    ' For more information see the following documents:\n'
    '  - Major changes in RHEL 9: {major_changes_url}\n'
    '  - Security Considerations in adopting RHEL 9: {crypto_policies_url}\n'
    ' The list of problematic packages: {bad_pkgs}'
)

REMEDY_HINT = (
    'It is recommended that you contact your package vendor and ask them for new'
    ' builds signed with supported signatures and install the new packages before'
    ' the upgrade. If this is not possible you may instead'
    ' remove the incompatible packages.'
)

MAJOR_CHANGE_URL = 'https://red.ht/rhel-9-overview-major-changes'
CRYPTO_POLICIES_URL = 'https://red.ht/rhel-9-security-considerations'


def _get_rpms_with_sha1_sig():
    installed_rpms = next(api.consume(InstalledRPM)).items
    return [pkg for pkg in installed_rpms if 'SHA1,' in pkg.pgpsig]


def _is_sha1_allowed(current_policy):
    """
    Return True if we are sure the current policy allows SHA-1 on RHEL 9. False otherwise

    The LEGACY policy and policies like DEFAULT:SHA1 enables SHA-1 on RHEL 9.
    """
    # TODO(pstodulk): this is just naive implementation
    # NOTE: The SHA1 sub policy does not exist on RHEL 8. It has to be created
    # manually by user in such a case.
    # NOTE: for now, limit the check for :SHA1 to DEFAULT:SHA1 only as otherwise we will
    # not be probably able to set correctly the policies inside the target
    # userspace container
    if current_policy == 'LEGACY' or "DEFAULT:SHA1" in current_policy:
        return True
    return False


def process():
    # TODO(pstodulk): add link to the official announce of the change in crypto policies
    bad_rpms = _get_rpms_with_sha1_sig()
    cpi = next(api.consume(CryptoPolicyInfo), None)
    if bad_rpms:
        bad_rpms_str = ''.join([
            '{prefix}{pkgname} ({sig})'.format(prefix=FMT_LIST_SEPARATOR, pkgname=pkg.name, sig=pkg.pgpsig)
            for pkg in bad_rpms
        ])
        report = [
            reporting.Title('Detected RPMs with RSA/SHA1 signature'),
            reporting.Summary(SUMMARY_FMT.format(
                major_changes_url=MAJOR_CHANGE_URL,
                crypto_policies_url=CRYPTO_POLICIES_URL,
                bad_pkgs=bad_rpms_str
            )),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SECURITY, reporting.Groups.SANITY]),
            reporting.Remediation(hint=REMEDY_HINT),
            reporting.ExternalLink(
                url=MAJOR_CHANGE_URL,
                title='Major changes in RHEL 9'
            ),
            reporting.ExternalLink(
                url=CRYPTO_POLICIES_URL,
                title='Security Considerations in adopting RHEL 9'
            )
        ]
        if not _is_sha1_allowed(cpi.current_policy):
            report.append(reporting.Groups([reporting.Groups.INHIBITOR]))
        reporting.create_report(report)
