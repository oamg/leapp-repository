import os.path

from leapp.libraries.common.reporting import report_generic

COROSYNC_CONF_LOCATION = "/etc/corosync/corosync.conf"
CIB_LOCATION = "/var/lib/pacemaker/cib/cib.xml"


def inhibit(node_type):
    report_generic(
        title="Use of HA cluster detected. Upgrade can't proceed.",
        summary=(
            "HA cluster is not supported by the inplace upgrade.\n"
            "HA cluster configuration file(s) found."
            " It seems to be a cluster {0}.".format(node_type)
        ),
        severity="high",
        flags=["inhibitor"],
    )


def check_ha_cluster():
    if os.path.isfile(COROSYNC_CONF_LOCATION):
        inhibit(node_type="node")
    elif os.path.isfile(CIB_LOCATION):
        inhibit(node_type="remote node")
