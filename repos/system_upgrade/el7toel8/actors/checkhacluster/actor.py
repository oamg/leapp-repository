from leapp.actors import Actor
from leapp.libraries.actor.checkhacluster import check_ha_cluster
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


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
