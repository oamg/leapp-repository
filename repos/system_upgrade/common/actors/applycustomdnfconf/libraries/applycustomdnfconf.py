import os

from leapp.libraries.stdlib import api, CalledProcessError, run

CUSTOM_DNF_CONF_PATH = "/etc/leapp/files/dnf.conf"


def process():
    if os.path.exists(CUSTOM_DNF_CONF_PATH):
        try:
            run(["mv", CUSTOM_DNF_CONF_PATH, "/etc/dnf/dnf.conf"])
        except (CalledProcessError, OSError) as e:
            api.current_logger().debug(
                "Failed to move /etc/leapp/files/dnf.conf to /etc/dnf/dnf.conf: {}".format(e)
            )
