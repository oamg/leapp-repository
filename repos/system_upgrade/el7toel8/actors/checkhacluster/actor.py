import os.path

from leapp.actors import Actor
from leapp.libraries.actor.library import COROSYNC_CONF_LOCATION, CIB_LOCATION
from leapp.libraries.common.reporting import report_generic
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

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

class Checkhacluster(Actor):
    """
    Check if HA Cluster is in use. If yes, inhibit the upgrade process.

    The system is considered as part of cluster if a corosync.conf file
    (/etc/corosync/corosync.conf) can be found there.
    Also the system can be a part of a cluster as a remote node. In such case
    a cib file (/var/lib/pacemaker/cib/cib.xml) can be found there.
    """

    name = "check_ha_cluster"
    consumes = ()
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        check_ha_cluster()
