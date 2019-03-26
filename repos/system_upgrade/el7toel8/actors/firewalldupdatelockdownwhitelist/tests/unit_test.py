from leapp.libraries.actor import private

import xml.etree.ElementTree as ElementTree


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

    assert private.updateFirewallConfigCommand(root, '/usr/bin/python -Es /usr/bin/firewall-config')


def test_firewalldupdatelockdownwhitelist_library_negative():
    root = ElementTree.fromstring(
        '''<?xml version="1.0" encoding="utf-8"?>
           <whitelist>
             <command name="/usr/bin/foobar"/>
           </whitelist>
        ''')

    assert not private.updateFirewallConfigCommand(root, '')
    assert not private.updateFirewallConfigCommand(root, '/usr/bin/python -Es /usr/bin/firewall-config')

    root = ElementTree.fromstring(
        '''<?xml version="1.0" encoding="utf-8"?>
           <whitelist>
             <command name="/usr/libexec/platform-python -s /usr/bin/firewall-config"/>
             <selinux context="system_u:system_r:NetworkManager_t:s0"/>
             <selinux context="system_u:system_r:virtd_t:s0-s0:c0.c1023"/>
             <user id="0"/>
           </whitelist>
        ''')

    assert not private.updateFirewallConfigCommand(root, '/usr/libexec/platform-python -s /usr/bin/firewall-config')
