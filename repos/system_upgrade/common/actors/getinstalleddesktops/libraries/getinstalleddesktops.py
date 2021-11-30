from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM


def get_installed_desktops():
    api.current_logger().info("  Detecting desktop environments  ")
    api.current_logger().info("==================================")

    # Detect installed desktops by one of the base rpm packages
    kde_desktop_installed = has_package(InstalledRPM, "kde-workspace")
    gnome_desktop_installed = has_package(InstalledRPM, "gnome-session")
    api.current_logger().info("* KDE installed: {0}".format(kde_desktop_installed))
    api.current_logger().info("* Gnome installed: {0}".format(gnome_desktop_installed))
    api.current_logger().info("----------------------------------")

    return {"gnome_installed": gnome_desktop_installed, "kde_installed": kde_desktop_installed}
