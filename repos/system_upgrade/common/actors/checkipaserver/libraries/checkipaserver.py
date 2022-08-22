from leapp import reporting
from leapp.libraries.common.config.version import get_source_major_version

MIGRATION_GUIDE_7 = (
    "https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux"
    "/8/html/installing_identity_management/migrate-7-to-8_migrating"
    )
# TBD: update the doc url when migration guide 8->9 becomes available
MIGRATION_GUIDE_8 = "https://red.ht/IdM-upgrading-RHEL-8-to-RHEL-9"
MIGRATION_GUIDES = {
    '7': MIGRATION_GUIDE_7,
    '8': MIGRATION_GUIDE_8
}


def ipa_inhibit_upgrade(ipainfo):
    """
    Create upgrade inhibitor for configured ipa-server
    """
    entries = [
        reporting.Title(
            "ipa-server does not support in-place upgrade"
        ),
        reporting.Summary(
            "An IdM server installation was detected on the system. IdM "
            "does not support in-place upgrade."
        ),
        reporting.Remediation(
            hint="Follow the IdM RHEL migration guide lines."
        ),
        reporting.ExternalLink(
            url=MIGRATION_GUIDES[get_source_major_version()],
            title="IdM migration guide",
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource("package", "ipa-server"),
    ]
    return reporting.create_report(entries)


def ipa_warn_pkg_installed(ipainfo):
    """
    Warn that unused ipa-server package is installed
    """
    if ipainfo.is_client_configured:
        summary = (
            "The ipa-server package is installed but only IdM client is "
            "configured on this system."
        )
    else:
        summary = (
            "The ipa-server package is installed but neither IdM server "
            "nor client is configured on this system."
        )
    entries = [
        reporting.Title(
            "ipa-server package is installed but no IdM is configured"
        ),
        reporting.Summary(summary),
        reporting.Remediation(
            hint="Remove unused ipa-server package",
            commands=[["yum", "remove", "-y", "ipa-server"]],
        ),
        reporting.ExternalLink(
            url=MIGRATION_GUIDES[get_source_major_version()],
            title="Migrating IdM from RHEL 7 to 8",
        ),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource("package", "ipa-server"),
    ]
    return reporting.create_report(entries)
