from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM


def get_kde_apps_info():
    installed = list()
    base_kde_apps = ("kde-baseapps",
                     "okular",
                     "ark",
                     "kdepim",
                     "konsole",
                     "gwenview",
                     "kdenetwork",
                     "kate",
                     "kwrite")

    api.current_logger().info("  Detecting installed KDE apps  ")
    api.current_logger().info("================================")
    for app in [application for application in base_kde_apps if has_package(InstalledRPM, application)]:
        api.current_logger().info("Application {0} is installed.".format(app))
        installed.append(app)
    api.current_logger().info("----------------------------------")

    return installed
