from leapp.actors import Actor
from leapp.libraries.actor.checkipaserver import (
    ipa_inhibit_upgrade,
    ipa_warn_pkg_installed,
)
from leapp.models import IpaInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckIPAServer(Actor):
    """
    Check for ipa-server and inhibit upgrade
    """

    name = "check_ipa_server"
    consumes = (IpaInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        for ipainfo in self.consume(IpaInfo):
            if ipainfo.is_server_configured:
                self.log.error(
                    "IdM server instance detected, inhibit upgrade"
                )
                ipa_inhibit_upgrade(ipainfo)
            elif ipainfo.has_server_package:
                self.log.info("Unused ipa-server package detected")
                ipa_warn_pkg_installed(ipainfo)
