from leapp.models import FirewalldLockdownWhitelist
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

    lockdown_config = FirewalldLockdownWhitelist()
    lockdown_config.firewall_config_command = '/usr/bin/python -Es /usr/bin/firewall-config'
    assert private.updateFirewalldLockdownWhitelistXML(root, lockdown_config)


def test_firewalldupdatelockdownwhitelist_library_negative():
    root = ElementTree.fromstring(
        '''<?xml version="1.0" encoding="utf-8"?>
           <whitelist>
             <command name="/usr/bin/foobar"/>
           </whitelist>
        ''')

    lockdown_config = FirewalldLockdownWhitelist()
    lockdown_config.firewall_config_command = ''
    assert not private.updateFirewalldLockdownWhitelistXML(root, lockdown_config)

    lockdown_config = FirewalldLockdownWhitelist()
    lockdown_config.firewall_config_command = '/usr/bin/python -Es /usr/bin/firewall-config'
    assert not private.updateFirewalldLockdownWhitelistXML(root, lockdown_config)

    root = ElementTree.fromstring(
        '''<?xml version="1.0" encoding="utf-8"?>
           <whitelist>
             <command name="/usr/libexec/platform-python -s /usr/bin/firewall-config"/>
             <selinux context="system_u:system_r:NetworkManager_t:s0"/>
             <selinux context="system_u:system_r:virtd_t:s0-s0:c0.c1023"/>
             <user id="0"/>
           </whitelist>
        ''')

    lockdown_config = FirewalldLockdownWhitelist()
    lockdown_config.firewall_config_command = '/usr/libexec/platform-python -s /usr/bin/firewall-config'
    assert not private.updateFirewalldLockdownWhitelistXML(root, lockdown_config)
