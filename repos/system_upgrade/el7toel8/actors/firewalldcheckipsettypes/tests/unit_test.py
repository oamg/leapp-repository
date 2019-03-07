from leapp.libraries.actor import private


def test_firewalldcheckipsettypes_library():
    assert private.isIpsetTypeSupportedByNftables('hash:mac')
    assert private.isIpsetTypeSupportedByNftables('hash:ip')
    assert private.isIpsetTypeSupportedByNftables('hash:net')


def test_firewalldcheckipsettypes_library_negative():
    assert not private.isIpsetTypeSupportedByNftables('hash:ip,mark')
    assert not private.isIpsetTypeSupportedByNftables('hash:ip,port')
    assert not private.isIpsetTypeSupportedByNftables('hash:ip,port,ip')
    assert not private.isIpsetTypeSupportedByNftables('hash:ip,port,net')
    assert not private.isIpsetTypeSupportedByNftables('hash:net,iface')
    assert not private.isIpsetTypeSupportedByNftables('hash:net,net')
    assert not private.isIpsetTypeSupportedByNftables('hash:net,port')
    assert not private.isIpsetTypeSupportedByNftables('hash:net,port,net')
