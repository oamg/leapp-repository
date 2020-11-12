from leapp import reporting

MIGRATION_GUIDE = (
    "https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux"
    "/8/html/installing_identity_management/migrate-7-to-8_migrating"
)


def ipa_inhibit_upgrade(ipainfo):
    """
    Create upgrade inhibitor for configured ipa-server
    """
    entries = [
        reporting.Title(
            "ipa-server does not support in-place upgrade from RHEL 7 to 8"
        ),
        reporting.Summary(
            "An IdM server installation was detected on the system. IdM "
            "does not support in-place upgrade to RHEL 8. Please follow "
            "the migration guide lines."
        ),
        reporting.Remediation(
            hint="Please follow the IdM RHEL 7 to 8 migration guide lines."
        ),
        reporting.ExternalLink(
            url=MIGRATION_GUIDE, title="Migrating IdM from RHEL 7 to 8",
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.INHIBITOR]),
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
            url=MIGRATION_GUIDE, title="Migrating IdM from RHEL 7 to 8",
        ),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource("package", "ipa-server"),
    ]
    return reporting.create_report(entries)
