def updateFirewalldLockdownWhitelistXML(root, lockdown_config):
    changed = False

    # Only update the command element that corresponds to firewall-config
    firewall_config_command = '/usr/libexec/platform-python -s /usr/bin/firewall-config'
    for command in root.iter('command'):
        if 'name' in command.attrib and \
           lockdown_config.firewall_config_command == command.attrib['name'] and \
           lockdown_config.firewall_config_command != firewall_config_command:
            command.attrib['name'] = firewall_config_command
            changed = True

    return changed
