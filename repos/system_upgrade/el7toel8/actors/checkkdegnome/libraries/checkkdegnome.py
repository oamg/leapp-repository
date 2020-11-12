from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import InstalledDesktopsFacts, InstalledKdeAppsFacts


def check_kde_gnome():
    desktop_facts = next(api.consume(InstalledDesktopsFacts))
    kde_desktop_installed = desktop_facts.kde_installed
    gnome_desktop_installed = desktop_facts.gnome_installed

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
                reporting.Title("The installed KDE environment is unavailable on RHEL 8."),
                reporting.Summary(
                    "Because the KDE desktop environment is not available on RHEL 8, all the KDE-related packages"
                    " would be removed during the upgrade. There would be no desktop environment installed after the"
                    " upgrade."),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([
                    reporting.Groups.DESKTOP,
                    reporting.Groups.INHIBITOR,
                ]),
                reporting.Remediation(
                    hint=("Remove KDE (at least the `kde-workspace` package) or install the GNOME desktop environment"
                          " to be able to upgrade."),
                    commands=[['yum', '-y', 'groupinstall', '"Server with GUI"']])
                ])
            return

        # Assume both GNOME and KDE are installed in this state
        api.current_logger().info("Upgrade can be performed, but KDE desktop will"
                                  " be removed in favor of GNOME")
        reporting.create_report([
            reporting.Title("Upgrade can be performed, but KDE will be uninstalled."),
            reporting.Summary("The KDE desktop environment is unavailable on RHEL 8. KDE will be uninstalled "
                              "in favor of GNOME during the upgrade."),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([
                reporting.Groups.DESKTOP
            ])])
        api.current_logger().info("----------------------------------")

    # At this state we just need to detect whether any KDE/Qt app is installed to inform user
    # that the application will be removed during the upgrade process. No matter if KDE is installed
    # or not.

    KDEAppsFacts = next(api.consume(InstalledKdeAppsFacts))
    if KDEAppsFacts.installed_apps:
        # upgrade can be performed, but user will loose KDE apps
        api.current_logger().info("Installed KDE/Qt apps detected.")
        reporting.create_report([
            reporting.Title("Upgrade can be performed, but KDE/Qt apps will be uninstalled."),
            reporting.Summary("The KDE desktop environment is unavailable on RHEL 8. "
                              "All the KDE/Qt apps will be removed during the upgrade, including but not limited "
                              "to:\n- {0}".format("\n- ".join(KDEAppsFacts.installed_apps))),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([
                reporting.Groups.DESKTOP
            ])])
    else:
        api.current_logger().info("No KDE app in use detected.")
        # upgrade can be performed
