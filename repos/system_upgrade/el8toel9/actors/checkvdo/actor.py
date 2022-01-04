from leapp.actors import Actor
from leapp.libraries.actor.checkvdo import check_vdo
from leapp.models import InstalledRedHatSignedRPM, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckVdo(Actor):
    """
    Check if vdo devices need to be migrated to lvm management.

    `Background`
    ============
    In RHEL 9.0 the indepdent VDO management software, `vdo manager`, is superseded
    by LVM management.  Existing VDOs must be converted to LVM-based management
    *before* upgrading to RHEL 9.0.

    The `CheckVdo` actor provides a pre-upgrade check for VDO devices that have
    not been converted and, if any are found, produces an inhibitory report during
    upgrade check phase.  If none are found `CheckVdo` produces a non-inhibitory
    report to that effect.

    As there currently exists the theoretical possibility that a VDO device may not
    complete its conversion to LVM-based management (e.g., via a poorly timed
    system crash during the conversion) `CheckVdo` also provides a pre-upgrade
    check for VDO devices in this state.  If any are found `CheckVdo` produces an
    inhibitory report during upgrade check phase.  If none are found `CheckVdo`
    does not produce a report concerning such VDO devices.

    `Overview`
    ==========
    `CheckVdo` relies almost exclusively on the default system-provided utilies
    `blkid` and `lsblk`.  The one `vdo manager` utility that `CheckVdo` utilizes is
    `vdoprepareforlvm`; this utility is used by `CheckVdo` to identify VDO devices
    which have not completed conversion to LVM-based management.  This dependence
    is necessary as only `vdoprepareforlvm` is programmatically aware of low-level
    format changes between pre- and post-conversion VDO devices.  As `vdo manager`
    is required to perform VDO device conversion to LVM-based management the
    dependency of `CheckVdo` on `vdoprepareforlvm` is not problematic.

    `CheckVdo` relies on the behaviors of `blkid` and `lsblk` in regard to pre- and
    post-conversion VDO devices.  Namely that both `blkid` and `lsblk` are able to
    identify pre-conversion VDO devices but do not identify post-conversion VDO
    devices as VDO devices.

    `Identifying Pre-conversion VDO devices`
    ========================================
    Pre-conversion VDO devices are easily identified via `blkid` using:

          blkid --output device --match-token TYPE=vdo

    `Identifying Post-conversion VDO devices`
    =========================================
    Identifying post-conversion VDO devices is more involved than pre-conversion
    ones.  As noted in `Overview` neither `blkid` nor `lsblk` are able to identify
    post-conversion VDO devices.  To identify post-conversion VDO devices the
    following process is used:

      1. Use `lsblk` to identify all block devices and their types

      2. Remove from the `lsblk` devices any whose type indicates it is a CD/DVD or
         VDO; if it is identified as VDO it must be a pre-conversion VDO

      3. Remove from the remaining devices any device that `blkid` can identify; if
         `blkid` can identify a device it cannot be a post-conversion VDO

      4. From the remaining devices select those which `vdoprepareforlvm` indicates
         are post-conversion VDOs

    Steps 2 & 3 minimize the set of devices that must be probed by `vdoprepareforlvm`.

    Step 4 may receive as input VDO devices created by LVM, either independently of
    `vdo manager` or as a result of successful conversion.  These devices appear to
    `vdoprepareforlvm` as pre-conversion VDO devices and are thus eliminated
    leaving only those devices which underwent VDO-level conversion but for which
    LVM did not complete taking over their management.
    """

    name = 'check_vdo'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(check_vdo())
