from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.libraries.stdlib.config import is_verbose
from leapp.models import ThirdPartyRPM

FMT_LIST_SEPARATOR = "\n    - "


def _generate_report(packages):
    """Generate a report with installed packages not signed by the distribution"""

    if not packages:
        return

    title = "Packages not signed by the distribution vendor found on the system"
    summary = (
        "The official solution for in-place upgrades contains instructions for"
        " the migration of packages signed by the vendor of the system"
        " distribution. Third-party content is not known to the upgrade"
        " process and it might need to be handled extra."
        " Third-party packages may be removed automatically during the upgrade if"
        " they depend on official distribution content which is not present on"
        " the target system - therefore RPM dependencies of such packages"
        " cannot be satisfied and hence such packages cannot be installed on"
        " the target system.\n\n"
        "The following packages have not been signed by the vendor of the"
        " distribution:{}{}"
    ).format(FMT_LIST_SEPARATOR, FMT_LIST_SEPARATOR.join(packages))
    hint = (
        "The most simple solution that does not require additional knowledge"
        " about the upgrade process is the uninstallation of such packages"
        " before the upgrade and installing these (or their newer versions"
        " compatible with the target system) back after the upgrade. Also you"
        " can just try to upgrade the system on a testing machine (or after"
        " the full system backup) to see the result.\n"
        "However, it is common use case to migrate or upgrade installed third"
        " party packages together with the system during the in-place upgrade"
        " process. To examine how to customize the process to deal with such"
        " packages, follow the documentation in the attached link"
        " for more details."
    )
    reporting.create_report(
        [
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY]),
            reporting.Remediation(hint=hint),
            reporting.ExternalLink(
                url="https://red.ht/customize-rhel-upgrade-actors",
                title="Handling the migration of your custom and third-party applications",
            ),
            # setting a stable key of the original, semantically equal, report
            # which was concerned with RHEL only
            reporting.Key("13f0791ae5f19f50e7d0d606fb6501f91b1efb2c")
        ]
    )

    if is_verbose():
        api.show_message(summary)


def get_third_party_pkgs():
    """Get a list of installed packages not signed by the distribution"""

    rpm_messages = api.consume(ThirdPartyRPM)
    data = next(rpm_messages, ThirdPartyRPM())
    if list(rpm_messages):
        api.current_logger().warning(
            "Unexpectedly received more than one ThirdPartyRPM message."
        )

    third_party_pkgs = list(set(pkg.name for pkg in data.items))
    third_party_pkgs.sort()
    return third_party_pkgs


def check_third_party_pkgs():
    """Check and generate a report if the system contains third-party installed packages"""
    _generate_report(get_third_party_pkgs())
