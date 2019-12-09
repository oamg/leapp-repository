import os
import subprocess
import time

from leapp import reporting
from leapp.libraries.stdlib import api

ONE_MONTH = 2592000  # Number of seconds in one month


def is_executable(path):
    """
    Checks if path exists, if it is file and if is executable.
    """
    return os.path.exists(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def get_xsession(path):
    """
    Gets current XSession.

    If there is more than one definition of xsession for some reason,
    function returns last definition. Return empty string if no XSession found in file given
    by path (any reason including bad path etc.)
    """
    default_xsession = ""
    if not isinstance(path, str):
        return default_xsession
    if not (os.path.exists(path) and os.path.isfile(path)):  # Bad path - in container for example
        return default_xsession
    with open(path, "r") as f:
        for line in f.readlines():
            if "xsession" in line.lower():
                default_xsession = line.split("=")[1].lower()
    return default_xsession


def check_app_in_use(app):
    """
    Method return True if application was used in last month, False in other cases.
    """
    path = "{0}/.kde/share/config/{1}rc".format(os.environ.get("HOME"), app)
    if os.path.isfile(path):
        last_modified = os.stat(path).st_mtime
        # Application is considered actively used, if it has been used in last month.
        return last_modified >= int(time.time() - ONE_MONTH)
    return False


def is_installed(app):
    """
    Wrapper for "rpm -q <app>" command

    Return value: True if application is found,
    False in other cases.
    Output of rpm command is not supressed.
    """
    return True if subprocess.call(["rpm", "-q", app]) == 0 else False


def check_kde_gnome():
    apps_in_use = 0
    api.current_logger().info("  Detecting desktop environments  ")
    api.current_logger().info("==================================")

    # Detect installed desktops by their startup files
    kde_desktop_installed = is_executable("/usr/bin/startkde")
    gnome_desktop_installed = is_executable("/usr/bin/gnome-session")
    api.current_logger().info("* KDE installed: {0}".format(kde_desktop_installed))
    api.current_logger().info("* Gnome installed: {0}".format(gnome_desktop_installed))
    api.current_logger().info("----------------------------------")

    # No desktop installed, we don't even care about apps as they are most likely not used or even installed
    if not kde_desktop_installed and not gnome_desktop_installed:
        api.current_logger().info("No desktop installed. Continuing with the upgrade.")
        return

    if kde_desktop_installed:
        api.current_logger().info("KDE desktop is installed. Checking what we can do about it.")
        if not gnome_desktop_installed:
            api.current_logger().error("Cannot perform the upgrade because there is"
                                       " no other desktop than KDE installed.")
            # We cannot continue with the upgrade process
            reporting.create_report([
                reporting.Title("Cannot upgrade because there is no other desktop than KDE installed."),
                reporting.Summary("With only KDE installed, there would be no other desktop after upgrade."),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Tags([
                    reporting.Tags.UPGRADE_PROCESS
                ]),
                reporting.Flags([
                    reporting.Flags.INHIBITOR
                ]),
                reporting.Remediation(
                    hint="Install GNOME desktop to be able to upgrade.")
                ])
            return

        # Assume GNOME is installed in this state

        user = os.environ.get("USER")
        default_xsession = get_xsession("/var/lib/AccountsService/users/{0}".format(user))
        if not default_xsession:
            api.current_logger().warn("Unable to detect default session.")
        else:
            if "plasma" in default_xsession:  # using in because there can be some white spaces
                api.current_logger().info("KDE used as default session.")
                api.current_logger().info("Upgrade can be performed, but KDE desktop will"
                                          " be removed in favor of GNOME")
                reporting.create_report([
                    reporting.Title("Upgrade can be performed, but KDE will be uninstalled."),
                    reporting.Summary("KDE has to be uninstalled in favor of GNOME to perform the upgrade."),
                    reporting.Severity(reporting.Severity.MEDIUM),
                    reporting.Tags([
                        reporting.Tags.UPGRADE_PROCESS
                    ])])
            else:
                api.current_logger().info("GNOME used as default session. Continuing with the upgrade.")
        api.current_logger().info("----------------------------------")

    # At this state we can assume that KDE desktop as such is not installed or used and we just need to
    # detect whether any KDE/Qt app is actively used to inform user that the application will be removed
    # during the upgrade process

    base_kde_apps = ("kde-baseapps",
                     "okular",
                     "ark",
                     "kdepim",
                     "konsole",
                     "gwenview",
                     "kdenetwork",
                     "kate", "kwrite")
    api.current_logger().info("  Detecting installed KDE apps  ")
    api.current_logger().info("================================")

    for app in base_kde_apps:
        if is_installed(app):
            if check_app_in_use(app):
                api.current_logger().info("Application {0} is actively used".format(app))
                apps_in_use += 1
        api.current_logger().info("* {0} {1} installed.".format(app, "is" if is_installed(app) else "is not"))

    api.current_logger().info("----------------------------------")

    if apps_in_use > 0:
        api.current_logger().info("KDE apps in use detected.")
        reporting.create_report([
            reporting.Title("Upgrade can be performed, but KDE apps will be uninstalled."),
            reporting.Summary("KDE apps will be removed to perform the upgrade."),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Tags([
                reporting.Tags.UPGRADE_PROCESS
            ]),
            reporting.Remediation(
                hint="KDE apps has to be removed, no other solution is possible.")
            ])
        # upgrade can be performed, but user will loose KDE desktop in favor of GNOME desktop
    else:
        api.current_logger().info("No KDE app in use detected.")
    # upgrade can be performed
