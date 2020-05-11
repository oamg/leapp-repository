def getLockdownFirewallConfigCommand(root):
    for command in root.iter('command'):
        if 'name' in command.attrib and \
           '/usr/bin/firewall-config' in command.attrib['name']:
            return command.attrib['name']

    return ''


def getEbtablesTablesInUse(root):
    tables = []
    for rule in root.iter('rule'):
        if 'ipv' in rule.attrib and rule.attrib['ipv'] == 'eb' and \
           'table' in rule.attrib and rule.attrib['table'] not in tables:
            tables.append(rule.attrib['table'])

    for passthrough in root.iter('passthrough'):
        if 'ipv' in passthrough.attrib and passthrough.attrib['ipv'] == 'eb':
            rule = passthrough.text.split()
            try:
                i = rule.index('-t')
                if rule[i + 1] not in tables:
                    tables.append(rule[i + 1])
            except ValueError:
                pass

    return tables


def getIpsetTypesInUse(root):
    types = []
    for ipset in root.iter('ipset'):
        if 'type' in ipset.attrib and ipset.attrib['type'] not in types:
            types.append(ipset.attrib['type'])
    return types
