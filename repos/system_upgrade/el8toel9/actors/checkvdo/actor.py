from leapp.actors import Actor
from leapp.dialogs import Dialog
from leapp.dialogs.components import BooleanComponent
from leapp.libraries.actor.checkvdo import check_vdo
from leapp.models import Report, VdoConversionInfo
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckVdo(Actor):
    """
    Check if VDO devices need to be migrated to lvm management.

    `Background`
    ============
    In RHEL 9.0 the indepdent VDO management software, `vdo manager`, is
    superseded by LVM management.  Existing VDOs must be converted to LVM-based
    management *before* upgrading to RHEL 9.0.

    The `CheckVdo` actor provides a pre-upgrade check for VDO devices that have
    not been converted and, if any are found, produces an inhibitory report
    during upgrade check phase.   If none are found `CheckVdo` does not produce
    a report concerning such VDO devices.

    As there currently exists the theoretical possibility that a VDO device may
    not complete its conversion to LVM-based management (e.g., via a poorly
    timed system crash during the conversion) `CheckVdo` also provides a
    pre-upgrade check for VDO devices in this state.  If any are found
    `CheckVdo` produces an inhibitory report during upgrade check phase.  If
    none are found `CheckVdo` does not produce a report concerning such VDO
    devices.

    If the VdoConversionInfo model indicates unexpected errors occurred during
    scanning CheckVdo will produce appropriate inhibitory reports.

    If the VdoConversionInfo model indicates conditions exist where VDO devices
    could exist but the necessary software to check was not installed on the
    system CheckVdo will present a dialog to the user. This dialog will ask the
    user to either install the required software if the user knows or is unsure
    that VDO devices exist or to approve the continuation of the upgrade if the
    user is certain that no VDO devices exist.

    To maximize safety CheckVdo will operate against all block devices which
    match the criteria for potential VDO devices.  Given the dynamic nature
    of device presence within a system some devices which may have been present
    during leapp discovery may not be present when CheckVdo runs.  As CheckVdo
    defaults to producing inhibitory reports if a device cannot be checked
    (for any reason) this dynamism may be problematic.  To prevent CheckVdo
    producing an inhibitory report for devices which are dynamically no longer
    present within the system the user may answer in the affirmative a dialog
    indicating that all VDO instances have been converted and the non-existence
    of a device is to be ignored.
    """

    name = 'check_vdo'
    consumes = (VdoConversionInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)
    dialogs = (
        Dialog(
            scope='check_vdo',
            reason='Confirmation',
            components=(
                BooleanComponent(
                    key='all_vdo_converted',
                    label='Are all VDO devices succesfully converted to LVM '
                          'management?',
                    description='Enter True if all VDO devices on the system '
                                'have been successfully converted to LVM '
                                'management.  Entering True will circumvent '
                                'checking block devices states as VDO devices '
                                'in need of conversion.  All VDO devices must '
                                'be converted to LVM management before '
                                'upgrading.',
                    reason='To maximize safety all block devices on a system '
                           'that meet the criteria as possible VDO devices '
                           'are checked to verify that, if VDOs, they have'
                           'been converted to LVM management.  If the check '
                           'of any device fails for any reason an upgrade'
                           'inhibiting report is generated.  This may be'
                           'problematic when devices are dynamically removed'
                           'from by the system subsequent to having been'
                           'identified during device discovery.  By '
                           'specifying that all VDO devices have been'
                           'successfully converted to LVM management the'
                           'checking of devices is not performed thus '
                           'avoiding any issues with checking devices.'
                ),
            )
        ),
        Dialog(
            scope='check_vdo',
            reason='Confirmation',
            components=(
                BooleanComponent(
                    key='no_vdo_devices',
                    label='Are there no VDO devices on the system?',
                    description='Enter True if there are no VDO devices on '
                                'the system and False continue the upgrade. '
                                'If the system has no VDO devices, then it '
                                'is safe to continue the upgrade. If there '
                                'are VDO devices they must all be converted '
                                'to LVM management before the upgrade can '
                                'proceed.',
                    reason='Based on installed packages it is possible that '
                           'VDO devices exist on the system.  All VDO devices '
                           'must be converted to being managed by LVM before '
                           'the upgrade occurs. Because the \'vdo\' package '
                           'is not installed, Leapp cannot determine whether '
                           'any VDO devices exist that have not yet been '
                           'converted.  If the devices are not converted and '
                           'the upgrade proceeds the data on unconverted VDO '
                           'devices will be inaccessible. If you have any '
                           'doubts you should choose to install the \'vdo\' '
                           'package and re-run the upgrade process to check '
                           'for unconverted VDO devices. If you are certain '
                           'that the system has no VDO devices or that all '
                           'VDO devices have been converted to LVM management '
                           'you may opt to allow the upgrade to proceed.'
                ),
            )
        ),
    )

    def get_all_vdo_converted_response(self):
        return self.get_answers(self.dialogs[0]).get('all_vdo_converted')

    def get_no_vdo_devices_response(self):
        return self.get_answers(self.dialogs[1]).get('no_vdo_devices')

    def process(self):
        for conversion_info in self.consume(VdoConversionInfo):
            check_vdo(conversion_info)
