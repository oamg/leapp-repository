from leapp import reporting
from leapp.actors import Actor
from leapp.models import ActiveKernelModulesFacts
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckNvidiaProprietaryDriver(Actor):
    """
    Check if NVIDIA proprietary driver is in use. If yes, inhibit the upgrade process.

    Updating bare metal (or VM) with the binary NVIDIA driver will end up with a blacklisted nouveau.

    See also https://bugzilla.redhat.com/show_bug.cgi?id=2057026
    """

    name = 'check_nvidia_proprietary_driver'
    consumes = (ActiveKernelModulesFacts,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):

        for fact in self.consume(ActiveKernelModulesFacts):
            nvidia_driver_loaded = any('nvidia' in active_mod.filename for active_mod in fact.kernel_modules)
            if nvidia_driver_loaded:
                create_report([
                    reporting.Title('Proprietary NVIDIA driver detected'),
                    reporting.Summary(
                            'Leapp has detected that the NVIDIA proprietary driver has been loaded, which also means '
                            'the nouveau driver is blacklisted. If you upgrade now, you will end up without a '
                            'graphical session, as the newer kernel won\'t be able to load the NVIDIA driver module '
                            'and nouveau will still be blacklisted.'
                            '\n\n'
                            'Please uninstall the NVIDIA graphics driver before upgrading to make sure you have a '
                            'graphical session after upgrading.'
                    ),
                    reporting.ExternalLink(
                            title='How to uninstall proprietary NVIDIA graphics driver and switch back to Red Hat '
                                  'shipped nouveau graphics driver?',
                            url='https://access.redhat.com/solutions/421683'
                    ),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.INHIBITOR]),
                    reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.DRIVERS]),
                ])
                break
