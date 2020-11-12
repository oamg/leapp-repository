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
        reporting.Groups([reporting.Groups.HIGH_AVAILABILITY, reporting.Groups.INHIBITOR]),
        reporting.ExternalLink(
            url="https://access.redhat.com/articles/2059253",
            title=(
                "Recommended Practices for Applying Software Updates"
                " to a RHEL High Availability or Resilient Storage Cluster"
            ),
        ),
        reporting.Remediation(
            hint=(
                "Destroy the existing HA cluster"
                " or (if you have already removed HA cluster packages) remove"
                " configuration files {0} and {1}".format(
                    CIB_LOCATION,
                    COROSYNC_CONF_LOCATION,
                )
            ),
            commands=[["sh", "-c", "pcs cluster stop --all --wait && pcs cluster destroy --all"]]
        ),
        reporting.RelatedResource('file', COROSYNC_CONF_LOCATION),
        reporting.RelatedResource('file', CIB_LOCATION)
    ])


def check_ha_cluster():
    if os.path.isfile(COROSYNC_CONF_LOCATION):
        inhibit(node_type="node")
    elif os.path.isfile(CIB_LOCATION):
        inhibit(node_type="remote node")
