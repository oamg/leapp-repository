from leapp.libraries.actor import private


def test_checkfirewalld_ipset():
    assert private.isIpsetTypeSupportedByNftables('hash:mac')
    assert private.isIpsetTypeSupportedByNftables('hash:ip')
    assert private.isIpsetTypeSupportedByNftables('hash:net')

    assert not private.isIpsetTypeSupportedByNftables('hash:ip,mark')
    assert not private.isIpsetTypeSupportedByNftables('hash:ip,port')
    assert not private.isIpsetTypeSupportedByNftables('hash:ip,port,ip')
    assert not private.isIpsetTypeSupportedByNftables('hash:ip,port,net')
    assert not private.isIpsetTypeSupportedByNftables('hash:net,iface')
    assert not private.isIpsetTypeSupportedByNftables('hash:net,net')
    assert not private.isIpsetTypeSupportedByNftables('hash:net,port')


def test_checkfirewalld_ebtables():
    assert private.isEbtablesTableSupported('nat')
    assert private.isEbtablesTableSupported('filter')

    assert not private.isEbtablesTableSupported('broute')
