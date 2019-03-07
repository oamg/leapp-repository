def isIpsetTypeSupportedByNftables(ipset_type):
    if ipset_type in ['hash:ip', 'hash:mac', 'hash:net']:
        return True

    return False
