from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.stdlib import format_list
from leapp.models import XorgDrvFacts
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

SUMMARY_XORG_DEPRECATE_DRIVERS_FMT = (
    'Leapp has detected the use of some deprecated Xorg drivers. '
    'Using these drivers could lead to a broken graphical session after the upgrade. '
    'Any custom configuration related to these drivers will be ignored. '
    'The list of used deprecated drivers:{}')

SUMMARY_XORG_DEPRECATE_DRIVERS_HINT = (
    'Please uninstall the Xorg driver and remove the corresponding driver '
    'customisation entries from the X.Org configuration files and directories, '
    'such as `/etc/X11/xorg.conf` and `/etc/X11/xorg.conf.d/` and reboot before '
    'upgrading to make sure you have a graphical session after upgrading.'
)


def _printable_drv(facts):
    items = []
    for fact in facts:
        for driver in fact.xorg_drivers:
            item = driver.driver
            if driver.has_options:
                item += ' (with custom driver options)'
            items.append(item)
    return format_list(items, callback_sort=None)


class XorgDrvCheck8to9(Actor):
    """
    Warn if Xorg deprecated drivers are in use.
    """

    name = 'xorgdrvcheck8to9'
    consumes = (XorgDrvFacts,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        facts = self.consume(XorgDrvFacts)
        deprecated_drivers = _printable_drv(facts)
        if len(deprecated_drivers) > 0:
            create_report([
                reporting.Title('Deprecated Xorg driver detected'),
                reporting.Summary(SUMMARY_XORG_DEPRECATE_DRIVERS_FMT.format(deprecated_drivers)),
                reporting.Severity(reporting.Severity.MEDIUM),
                reporting.Groups([reporting.Groups.DRIVERS]),
                reporting.Remediation(hint=SUMMARY_XORG_DEPRECATE_DRIVERS_HINT)
                ])
