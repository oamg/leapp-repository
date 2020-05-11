import xml.etree.ElementTree as ElementTree

from leapp.libraries.actor import firewalldupdatelockdownwhitelist


def test_firewalldupdatelockdownwhitelist_library():
    root = ElementTree.fromstring(
        '''<?xml version="1.0" encoding="utf-8"?>
           <whitelist>
             <command name="/usr/bin/python -Es /usr/bin/firewall-config"/>
             <command name="/usr/bin/foobar"/>
             <selinux context="system_u:system_r:NetworkManager_t:s0"/>
             <selinux context="system_u:system_r:virtd_t:s0-s0:c0.c1023"/>
             <user id="0"/>
           </whitelist>
        ''')

    assert firewalldupdatelockdownwhitelist.updateFirewallConfigCommand(
        root,
        '/usr/bin/python -Es /usr/bin/firewall-config'
    )


def test_firewalldupdatelockdownwhitelist_library_negative():
    root = ElementTree.fromstring(
        '''<?xml version="1.0" encoding="utf-8"?>
           <whitelist>
             <command name="/usr/bin/foobar"/>
           </whitelist>
        ''')

    assert not firewalldupdatelockdownwhitelist.updateFirewallConfigCommand(root, '')
    assert not firewalldupdatelockdownwhitelist.updateFirewallConfigCommand(
        root,
        '/usr/bin/python -Es /usr/bin/firewall-config'
    )

    root = ElementTree.fromstring(
        '''<?xml version="1.0" encoding="utf-8"?>
           <whitelist>
             <command name="/usr/libexec/platform-python -s /usr/bin/firewall-config"/>
             <selinux context="system_u:system_r:NetworkManager_t:s0"/>
             <selinux context="system_u:system_r:virtd_t:s0-s0:c0.c1023"/>
             <user id="0"/>
           </whitelist>
        ''')

    assert not firewalldupdatelockdownwhitelist.updateFirewallConfigCommand(
        root,
        '/usr/libexec/platform-python -s /usr/bin/firewall-config'
    )
