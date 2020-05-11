def updateFirewallConfigCommand(root, old_command):
    changed = False

    # Only update the command element that corresponds to firewall-config
    new_command = '/usr/libexec/platform-python -s /usr/bin/firewall-config'
    for command in root.iter('command'):
        if 'name' in command.attrib and \
           old_command == command.attrib['name'] and \
           old_command != new_command:
            command.attrib['name'] = new_command
            changed = True

    return changed
