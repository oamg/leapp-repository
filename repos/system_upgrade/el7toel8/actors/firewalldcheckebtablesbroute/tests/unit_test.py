from leapp.libraries.actor import private

import xml.etree.ElementTree as ElementTree


def test_firewalldcheckebtablesbroute_library():
    root = ElementTree.fromstring(
        '''<?xml version="1.0" encoding="utf-8"?>
           <direct>
             <passthrough ipv="eb">-t broute -I BROUTING 1 -j ACCEPT</passthrough>
           </direct>
        ''')
    assert private.isEbtablesBrouteTableInUse(root)

    root = ElementTree.fromstring(
        '''<?xml version="1.0" encoding="utf-8"?>
           <direct>
             <rule priority="1" table="broute" ipv="eb" chain="BROUTING">-j ACCEPT</rule>
           </direct>
        ''')
    assert private.isEbtablesBrouteTableInUse(root)

    root = ElementTree.fromstring(
        '''<?xml version="1.0" encoding="utf-8"?>
           <direct>
             <rule priority="1" table="broute" ipv="eb" chain="BROUTING">-j ACCEPT</rule>
             <passthrough ipv="eb">-t broute -I BROUTING 1 -j ACCEPT</passthrough>
           </direct>
        ''')
    assert private.isEbtablesBrouteTableInUse(root)


def test_firewalldcheckebtablesbroute_library_negative():
    root = ElementTree.fromstring(
        '''<?xml version="1.0" encoding="utf-8"?>
           <direct>
             <rule priority="1" table="filter" ipv="ipv4" chain="INPUT">-j ACCEPT</rule>
             <passthrough ipv="ipv4">-t filter -I BROUTING 1 -j ACCEPT</passthrough>
           </direct>
        ''')
    assert not private.isEbtablesBrouteTableInUse(root)
