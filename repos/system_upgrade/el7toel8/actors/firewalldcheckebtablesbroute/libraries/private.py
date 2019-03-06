def isEbtablesBrouteTableInUse(root):
    for rule in root.iter('rule'):
        if 'ipv' in rule.attrib and rule.attrib['ipv'] == 'eb' and \
           'table' in rule.attrib and rule.attrib['table'] == 'broute':
            return True

    for passthrough in root.iter('passthrough'):
        if 'ipv' in passthrough.attrib and passthrough.attrib['ipv'] == 'eb':
            rule = passthrough.text.split()
            try:
                i = rule.index('-t')
                if rule[i+1] == 'broute':
                    return True
            except ValueError:
                pass
            
    return False
