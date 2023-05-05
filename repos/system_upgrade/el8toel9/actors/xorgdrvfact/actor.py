from leapp.actors import Actor
from leapp.libraries.actor.xorgdriverlib import check_drv_and_options, get_xorg_logs_from_journal
from leapp.libraries.stdlib import api
from leapp.models import XorgDrvFacts
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class XorgDrvFacts8to9(Actor):
    """
    Check the journal logs for deprecated Xorg drivers.

    This actor checks the journal logs and looks for deprecated Xorg drivers.
    """

    name = 'xorgdrvfacts8to9'
    consumes = ()
    produces = (XorgDrvFacts,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        xorg_logs = get_xorg_logs_from_journal()
        deprecated_drivers = []
        for driver in ['RADEON', 'ATI', 'AMDGPU', 'MACH64', 'intel', 'spiceqxl', 'qxl', 'NOUVEAU', 'NV', 'VESA']:
            deprecated_driver = check_drv_and_options(driver, xorg_logs)
            if deprecated_driver:
                deprecated_drivers.append(deprecated_driver)

        api.produce(XorgDrvFacts(xorg_drivers=deprecated_drivers))
