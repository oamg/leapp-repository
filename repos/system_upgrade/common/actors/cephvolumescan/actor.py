from leapp.actors import Actor
from leapp.libraries.actor import cephvolumescan
from leapp.models import CephInfo, InstalledRPM
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CephVolumeScan(Actor):

    """
    Retrieves the list of encrypted Ceph OSD
    """

    name = 'cephvolumescan'
    consumes = (InstalledRPM,)
    produces = (CephInfo,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        output = cephvolumescan.encrypted_osds_list()
        self.produce(CephInfo(encrypted_volumes=output))
