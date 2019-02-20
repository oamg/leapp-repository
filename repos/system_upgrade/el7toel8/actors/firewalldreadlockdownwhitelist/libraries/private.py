from leapp.models import FirewalldLockdownWhitelist


def getFirewalldLockdownWhitelistFromXML(root):
    lockdown_config = FirewalldLockdownWhitelist()

    for command in root.iter('command'):
        if 'name' in command.attrib and \
           '/usr/bin/firewall-config' in command.attrib['name']:
            lockdown_config.firewall_config_command = command.attrib['name']
            break

    return lockdown_config
