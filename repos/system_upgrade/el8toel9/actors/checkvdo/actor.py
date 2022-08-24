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
    In RHEL 9.0 the independent VDO management software, `vdo manager`, is
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
    user is certain that either there are no VDO devices present or that all
    VDO devices have been successfully converted.

    To maximize safety CheckVdo operates against all block devices which
    match the criteria for potential VDO devices.  Given the dynamic nature
    of device presence within a system some devices which may have been present
    during leapp discovery may not be present when CheckVdo runs.  As CheckVdo
    defaults to producing inhibitory reports if a device cannot be checked
    (for any reason) this dynamism may be problematic.  To prevent CheckVdo
    producing an inhibitory report for devices which are dynamically no longer
    present within the system the user may answer the previously mentioned
    dialog in the affirmative when the user knows that all VDO devices have
    been converted.  This will circumvent checks of block devices.
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
                    key='confirm',
                    label='Are all VDO devices, if any, successfully converted to LVM management?',
                    description='Enter True if no VDO devices are present '
                                'on the system or all VDO devices on the system '
                                'have been successfully converted to LVM '
                                'management. '
                                'Entering True will circumvent check of failures '
                                'and undetermined devices. '
                                'Recognized VDO devices that have not been '
                                'converted to LVM management can still block '
                                'the upgrade despite the answer.'
                                'All VDO devices must be converted to LVM '
                                'management before upgrading.',
                    reason='To maximize safety all block devices on a system '
                           'that meet the criteria as possible VDO devices '
                           'are checked to verify that, if VDOs, they have '
                           'been converted to LVM management. '
                           'If the devices are not converted and the upgrade '
                           'proceeds the data on unconverted VDO devices will '
                           'be inaccessible. '
                           'In order to perform checking the \'vdo\' package '
                           'must be installed. '
                           'If the \'vdo\' package is not installed and there '
                           'are any doubts the \'vdo\' package should be '
                           'installed and the upgrade process re-run to check '
                           'for unconverted VDO devices. '
                           'If the check of any device fails for any reason '
                           'an upgrade inhibiting report is generated. '
                           'This may be problematic if devices are '
                           'dynamically removed from the system subsequent to '
                           'having been identified during device discovery. '
                           'If it is certain that all VDO devices have been '
                           'successfully converted to LVM management this '
                           'dialog may be answered in the affirmative which '
                           'will circumvent block device checking.'
                ),
            )
        ),
    )
    _asked_answer = False
    _vdo_answer = None

    def get_vdo_answer(self):
        if not self._asked_answer:
            self._asked_answer = True
            # calling this multiple times could lead to possible issues
            # or at least in redundant reports
            self._vdo_answer = self.get_answers(self.dialogs[0]).get('confirm')
        return self._vdo_answer

    def process(self):
        for conversion_info in self.consume(VdoConversionInfo):
            check_vdo(conversion_info)
