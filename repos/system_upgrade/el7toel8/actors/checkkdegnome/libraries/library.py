from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import InstalledDesktopsFacts, InstalledKdeAppsFacts


def check_kde_gnome():
    desktopFacts = next(api.consume(InstalledDesktopsFacts))
    kde_desktop_installed = desktopFacts.kde_installed
    gnome_desktop_installed = desktopFacts.gnome_installed

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
                reporting.Summary("With only KDE installed, there would be no other desktop env. after upgrade."),
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
        else:
            # Assume both GNOME and KDE are installed in this state
            api.current_logger().info("Upgrade can be performed, but KDE desktop will"
                                      " be removed in favor of GNOME")
            reporting.create_report([
                reporting.Title("Upgrade can be performed, but KDE will be uninstalled."),
                reporting.Summary("KDE has to be uninstalled in favor of GNOME to perform the upgrade."),
                reporting.Severity(reporting.Severity.MEDIUM),
                reporting.Tags([
                    reporting.Tags.UPGRADE_PROCESS
                ])])
        api.current_logger().info("----------------------------------")

    # At this state we just need to detect whether any KDE/Qt app is installed to inform user
    # that the application will be removed during the upgrade process. No matter if KDE is installed
    # or not.

    KDEAppsFacts = next(api.consume(InstalledKdeAppsFacts))
    apps_in_use = KDEAppsFacts.installed_apps
    if apps_in_use:
        # upgrade can be performed, but user will loose KDE apps
        api.current_logger().info("Installed KDE/Qt apps detected.")
        reporting.create_report([
            reporting.Title("Upgrade can be performed, but KDE/Qt apps will be uninstalled."),
            reporting.Summary("KDE/Qt apps will be removed to perform the upgrade."),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Tags([
                reporting.Tags.UPGRADE_PROCESS
            ])])
    else:
        api.current_logger().info("No KDE app in use detected.")
        # upgrade can be performed
