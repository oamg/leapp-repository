from leapp import reporting
from leapp.libraries.common import rhsm
from leapp.libraries.common.config import get_env
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM, RpmTransactionTasks

INSIGHTS_CLIENT_PKG = "insights-client"


def _ensure_package(package):
    """
    Produce install tasks if the given package is missing

    :return: True if the install task is produced else False
    """
    has_client_package = has_package(InstalledRPM, package)
    if not has_client_package:
        api.produce(RpmTransactionTasks(to_install=[package]))

    return not has_client_package


def _report_registration_info(installing_client):
    pkg_msg = " The '{}' package required for the registration will be installed during the upgrade."

    title = "Automatic registration into Red Hat Insights"
    summary = (
        "After the upgrade, this system will be automatically registered into Red Hat Insights."
        "{}"
        " To skip the automatic registration, use the '--no-insights-register' command line option or"
        " set the LEAPP_NO_INSIGHTS_REGISTER environment variable."
    ).format(pkg_msg.format(INSIGHTS_CLIENT_PKG) if installing_client else "")

    reporting.create_report(
        [
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Groups([reporting.Groups.SERVICES]),
        ]
    )


def process():
    if rhsm.skip_rhsm():
        return

    if get_env("LEAPP_NO_INSIGHTS_REGISTER", "0") == "1":
        return

    installing_client = _ensure_package(INSIGHTS_CLIENT_PKG)
    _report_registration_info(installing_client)
