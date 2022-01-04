from leapp.actors import Actor
from leapp.libraries.actor import vdoconversionscanner
from leapp.models import InstalledRedHatSignedRPM, StorageInfo, VdoConversionInfo
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class VdoConversionScanner(Actor):
    """
    Provides conversion info about VDO devices.

    A VdoConversionInfo message containing the data will be produced.

    In RHEL 9.0 the indepdent VDO management software, `vdo manager`, is
    superseded by LVM management.  Existing VDOs must be converted to LVM-based
    management *before* upgrading to RHEL 9.0.

    The `VdoConversionScanner` actor provides a pre-upgrade check for VDO
    devices.  Consuming the StorageInfo model `VdoConversionScanner` iterates
    over the contained lsblk information and checks each disk or partition for
    being a VDO device.  There are three categories of devices in the eyes of
    `VdoConversionScanner`:

      - not a VDO device
      - a pre-conversion VDO device
      - a post-conversion VDO device

    Those devices identified as not a VDO device are skipped.  Those identified
    as pre-conversion VDOs have their identifying data stored in a
    VdoPreConversion model; their simple existence is sufficient reason to
    prevent upgrade.  Devices identified as a post-conversion VDO device
    require an additional check to determine if they should prevent upgrade.

    Theoretically a VDO device may not complete its conversion to LVM-based
    management (e.g., via a poorly timed system crash during the conversion).
    For those VDO device's identified (at VDO level) as post-conversion
    `VdoConversionScanner` performs an additional check to determine if the
    device is identified by blkid as an LVM2_member.  This information is
    recorded in the VdoPostConversion model.

    Note that unexpected exit codes from querying a device to identify if it is
    a VDO device or from from blkid in checking if the VDO device has completed
    conversion to LVM-based management will cause VdoConversionScanner to
    generate an inhibitory report as without being able to obtain the necessary
    information the only safe course of action is to prevent upgrade.

    The generated VdoPreConversion and VdoPostConversion models are used
    together to produce the VdoConversionInfo model.  This latter model is
    consumed by the CheckVdo actor (executed during ChecksPhase) which, based
    on the contents of the model, may produce an upgrade inhibitory report.
    """

    name = 'vdo_conversion_scanner'
    consumes = (InstalledRedHatSignedRPM, StorageInfo)
    produces = (Report, VdoConversionInfo)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        for storqge_info in self.consume(StorageInfo):
            self.produce(vdoconversionscanner.get_info(storqge_info))
