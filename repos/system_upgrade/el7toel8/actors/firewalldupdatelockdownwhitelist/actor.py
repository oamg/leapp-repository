import xml.etree.ElementTree as ElementTree

from leapp.actors import Actor
from leapp.libraries.actor import firewalldupdatelockdownwhitelist
from leapp.models import FirewalldFacts
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class FirewalldUpdateLockdownWhitelist(Actor):
    """
    Update the firewalld Lockdown Whitelist.

    RHEL-8 uses a platform specific python interpreter for packaged
    applications. For firewall-config, the interpreter path is part of the
    lockdown list. In RHEL-7 this was simply /usr/bin/python, but in RHEL-8
    it's /usr/libexec/platform-python. However, if the user made changes to the
    lockdown whitelist it won't be replaced by RPM/dnf. As such we must update
    the interpreter if the old value is there.
    """

    name = 'firewalld_update_lockdown_whitelist'
    consumes = (FirewalldFacts,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        for facts in self.consume(FirewalldFacts):
            if facts.firewall_config_command:
                tree = ElementTree.parse('/etc/firewalld/lockdown-whitelist.xml')
                root = tree.getroot()

                need_write = firewalldupdatelockdownwhitelist.updateFirewallConfigCommand(
                    root,
                    facts.firewall_config_command
                )

                if need_write:
                    tree.write('/etc/firewalld/lockdown-whitelist.xml')
                    self.log.info('Updated lockdown whitelist')
