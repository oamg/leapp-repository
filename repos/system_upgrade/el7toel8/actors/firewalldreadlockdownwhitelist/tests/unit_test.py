from leapp.libraries.actor import private

import xml.etree.ElementTree as ElementTree


def test_firewalldreadlockdownwhitelist_library():
    root = ElementTree.fromstring(
        '''<?xml version="1.0" encoding="utf-8"?>
           <whitelist>
             <command name="/usr/bin/python -Es /usr/bin/firewall-config"/>
             <selinux context="system_u:system_r:NetworkManager_t:s0"/>
             <selinux context="system_u:system_r:virtd_t:s0-s0:c0.c1023"/>
             <user id="0"/>
           </whitelist>
        ''')

    lockdown_config = private.getFirewalldLockdownWhitelistFromXML(root)
    assert lockdown_config.firewall_config_command == '/usr/bin/python -Es /usr/bin/firewall-config'


def test_firewalldreadlockdownwhitelist_library_negative():
    root = ElementTree.fromstring(
        '''<?xml version="1.0" encoding="utf-8"?>
           <whitelist>
             <command name="/usr/bin/foobar"/>
             <selinux context="system_u:system_r:NetworkManager_t:s0"/>
             <selinux context="system_u:system_r:virtd_t:s0-s0:c0.c1023"/>
             <user id="0"/>
           </whitelist>
        ''')

    lockdown_config = private.getFirewalldLockdownWhitelistFromXML(root)
    assert lockdown_config.firewall_config_command == ''
