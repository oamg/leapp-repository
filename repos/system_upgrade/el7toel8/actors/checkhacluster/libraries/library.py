import os.path

from leapp import reporting
from leapp.reporting import create_report

COROSYNC_CONF_LOCATION = "/etc/corosync/corosync.conf"
CIB_LOCATION = "/var/lib/pacemaker/cib/cib.xml"


def inhibit(node_type):
    create_report([
        reporting.Title("Use of HA cluster detected. Upgrade can't proceed."),
        reporting.Summary(
            "HA cluster is not supported by the inplace upgrade.\n"
            "HA cluster configuration file(s) found."
            " It seems to be a cluster {0}.".format(node_type)
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Tags([reporting.Tags.HIGH_AVAILABILITY]),
        reporting.Flags([reporting.Flags.INHIBITOR]),
        reporting.RelatedResource('file', COROSYNC_CONF_LOCATION),
        reporting.RelatedResource('file', CIB_LOCATION)
    ])


def check_ha_cluster():
    if os.path.isfile(COROSYNC_CONF_LOCATION):
        inhibit(node_type="node")
    elif os.path.isfile(CIB_LOCATION):
        inhibit(node_type="remote node")
