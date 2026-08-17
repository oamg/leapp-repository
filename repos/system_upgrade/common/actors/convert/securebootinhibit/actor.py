from leapp.actors import Actor
from leapp.dialogs import Dialog
from leapp.dialogs.components import BooleanComponent
from leapp.libraries.actor import securebootinhibit
from leapp.models import FirmwareFacts
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class SecureBootInhibit(Actor):
    """
    Inhibit the conversion if SecureBoot is enabled.

    When EFI runtime variables are inaccessible and the Secure Boot state
    cannot be determined automatically, the user is asked to confirm the
    state via a dialog.
    """

    name = 'secure_boot_inhibit'
    consumes = (FirmwareFacts,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)
    dialogs = (
        Dialog(
            scope='secure_boot_inhibit',
            reason='Confirmation',
            components=(
                BooleanComponent(
                    key='confirm_secureboot_enabled',
                    label='Is Secure Boot enabled on this system?',
                    description=(
                        'Set to True if Secure Boot is enabled, False if disabled.'
                        ' If unsure, check your UEFI firmware settings.'
                    ),
                    reason=(
                        'The Secure Boot state cannot be determined automatically'
                        ' because UEFI runtime variables are not accessible.'
                    ),
                ),
            ),
        ),
    )

    _asked_answer = False
    _sb_answer = None

    def get_sb_answer(self):
        if not self._asked_answer:
            self._asked_answer = True
            self._sb_answer = self.get_answers(self.dialogs[0]).get('confirm_secureboot_enabled')
        return self._sb_answer

    def process(self):
        securebootinhibit.process()
