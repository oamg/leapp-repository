from leapp.actors import Actor
from leapp.libraries.actor import vdoconversionscanner
from leapp.models import InstalledRedHatSignedRPM, StorageInfo, VdoConversionInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class VdoConversionScanner(Actor):
    """
    Provides conversion info about VDO devices.

    A VdoConversionInfo message containing the data will be produced.

    In RHEL 9.0 the independent VDO management software, `vdo manager`, is
    superseded by LVM management.  Existing VDOs must be converted to LVM-based
    management *before* upgrading to RHEL 9.0.

    The `VdoConversionScanner` actor provides a pre-upgrade check for VDO
    devices.  Consuming the StorageInfo model `VdoConversionScanner` iterates
    over the contained lsblk information and checks each disk or partition for
    being a VDO device.  There are four categories of devices in the eyes of
    `VdoConversionScanner`:

      - not a VDO device
      - a pre-conversion VDO device
      - a post-conversion VDO device
      - a device not falling into any of the above

    Attempts to definitively identify a device as belonging to one of the first
    three listed categories above may fail.  These devices may or may not be an
    issue for upgrade.

    If a device could not be identified as either a VDO device or not results
    in that device's information being recorded in a
    VdoConversionUndeterminedDevice model.  This includes both the situation
    where LVM is installed on the system but the VDO management software is
    not as well as the situation where both are installed but the check of
    the device encountered an unexpected error.

    Devices identified as not a VDO device are skipped.

    Devices identified as pre-conversion VDOs have their identifying data
    stored in a VdoConversionPreDevice model; their simple existence is
    sufficient reason to prevent upgrade.

    A post-conversion (at VDO level) VDO device may not have completed its
    conversion to LVM-based management (e.g., via a poorly timed system crash
    during the conversion). For those VDO device's identified as
    post-conversion `VdoConversionScanner` performs an additional check to
    determine if the device is identified by blkid as an LVM2_member.  As the
    invocation of blkid may fail for reasons outside this scanner's control if
    such happens the device's completion status will be set to indicate it did
    not complete conversion.

    The generated VdoConversionPostDevice, VdoConversionPreDevice and
    VdoConversionUndeterminedDevice models are used together to produce the
    VdoConversionInfo model.  This latter model is consumed by the CheckVdo
    actor (executed during ChecksPhase) which, based on the contents of the
    model, may produce upgrade inhibitory reports.
    """

    name = 'vdo_conversion_scanner'
    consumes = (InstalledRedHatSignedRPM, StorageInfo)
    produces = (VdoConversionInfo,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        for storage_info in self.consume(StorageInfo):
            self.produce(vdoconversionscanner.get_info(storage_info))
