from leapp.libraries.actor.private_firewalldcollectusedobjectnames import (
    get_used_services,
    get_used_services_tuple,
    is_policy_in_use,
    is_zone_in_use,
    is_zone_in_use_tuple
)


def test_is_zone_in_use():
    conf = {'interfaces': ['dummy0'],
            'services': ['tftp-client']}
    assert is_zone_in_use(conf)

    conf = {'sources': ['10.1.2.0/24'],
            'services': ['tftp-client']}
    assert is_zone_in_use(conf)

    conf = {'interfaces': ['dummy0'],
            'sources': ['fd00::/8'],
            'services': ['tftp-client']}
    assert is_zone_in_use(conf)


def test_is_zone_in_use_tuple():
    conf = (None, None, None, None, None,
            ['tftp-client'],  # conf[5], services
            None, None, None, None,
            ['dummy0'],  # conf[10], interfaces
            [],  # conf[11], sources
            [],  # conf[12], rules_str
            None, None, None)
    assert is_zone_in_use_tuple(conf)

    conf = (None, None, None, None, None,
            ['tftp-client'],  # conf[5], services
            None, None, None, None,
            [],  # conf[10], interfaces
            ['10.1.2.0/24'],  # conf[11], sources
            [],  # conf[12], rules_str
            None, None, None)
    assert is_zone_in_use_tuple(conf)

    conf = (None, None, None, None, None,
            ['tftp-client'],  # conf[5], services
            None, None, None, None,
            ['dummy0'],  # conf[10], interfaces
            ['fd00::/8'],  # conf[11], sources
            [],  # conf[12], rules_str
            None, None, None)
    assert is_zone_in_use_tuple(conf)


def test_is_zone_in_use_negative():
    conf = {'interfaces': [],
            'services': ['tftp-client']}
    assert not is_zone_in_use(conf)

    conf = {'sources': [],
            'services': ['tftp-client']}
    assert not is_zone_in_use(conf)

    conf = {'services': ['tftp-client']}
    assert not is_zone_in_use(conf)


def test_is_zone_in_use_tuple_negative():
    conf = (None, None, None, None, None,
            ['tftp-client'],  # conf[5], services
            None, None, None, None,
            [],  # conf[10], interfaces
            [],  # conf[11], sources
            [],  # conf[12], rules_str
            None, None, None)
    assert not is_zone_in_use_tuple(conf)


def test_is_policy_in_use():
    conf = {'ingress_zones': ['HOST'],
            'egress_zones': ['public'],
            'services': ['tftp-client']}
    used_zones = ['public']
    assert is_policy_in_use(conf, used_zones)

    conf = {'ingress_zones': ['internal'],
            'egress_zones': ['external'],
            'services': []}
    used_zones = ['internal', 'external']
    assert is_policy_in_use(conf, used_zones)

    conf = {'ingress_zones': ['internal'],
            'egress_zones': ['external'],
            'services': []}
    used_zones = ['internal', 'external', 'public']
    assert is_policy_in_use(conf, used_zones)


def test_is_policy_in_use_negative():
    conf = {'ingress_zones': ['HOST'],
            'egress_zones': ['public'],
            'services': ['tftp-client']}
    used_zones = ['home']
    assert not is_policy_in_use(conf, used_zones)

    conf = {'ingress_zones': ['internal'],
            'egress_zones': ['external'],
            'services': []}
    used_zones = ['public', 'external']
    assert not is_policy_in_use(conf, used_zones)

    conf = {'egress_zones': ['external'],
            'services': []}
    used_zones = ['internal', 'public']
    assert not is_policy_in_use(conf, used_zones)


def test_get_used_services_zone():
    conf = {'interfaces': ['dummy0'],
            'services': ['tftp-client']}
    assert 'tftp-client' in get_used_services(conf, True)

    conf = {'sources': ['10.1.2.0/24'],
            'rules_str': ['rule family="ipv4" source address="10.1.1.0/24" service name="tftp-client" reject']}
    assert 'tftp-client' in get_used_services(conf, True)

    conf = {'interfaces': ['dummy0'],
            'sources': ['fd00::/8'],
            'rules_str': ['rule service name="ssh" accept',
                          'rule service name="tftp-client" accept']}
    assert 'tftp-client' in get_used_services(conf, True)


def test_get_used_services_tuple_zone():
    conf = (None, None, None, None, None,
            ['tftp-client'],  # conf[5], services
            None, None, None, None,
            ['dummy0'],  # conf[10], interfaces
            [],  # conf[11], sources
            [],  # conf[12], rules_str
            None, None, None)
    assert 'tftp-client' in get_used_services_tuple(conf, True)

    conf = (None, None, None, None, None,
            [],  # conf[5], services
            None, None, None, None,
            [],  # conf[10], interfaces
            ['10.1.2.0/24'],  # conf[11], sources
            ['rule family="ipv4" source address="10.1.1.0/24" service name="tftp-client" reject'],
            None, None, None)
    assert 'tftp-client' in get_used_services_tuple(conf, True)

    conf = (None, None, None, None, None,
            [],  # conf[5], services
            None, None, None, None,
            ['dummy0'],  # conf[10], interfaces
            ['fd00::/8'],  # conf[11], sources
            ['rule service name="ssh" accept', 'rule service name="tftp-client" accept'],  # conf[12], rules_str
            None, None, None)
    assert 'tftp-client' in get_used_services_tuple(conf, True)


def test_get_used_services_zone_negative():
    conf = {'interfaces': ['dummy0'],
            'services': ['https']}
    assert 'tftp-client' not in get_used_services(conf, True)

    conf = {'sources': ['10.1.2.0/24'],
            'rules_str': ['rule family="ipv4" source address="10.1.1.0/24" service name="ssh" reject'],
            'services': ['https']}
    assert 'tftp-client' not in get_used_services(conf, True)

    conf = {'interfaces': ['dummy0'],
            'sources': ['fd00::/8'],
            'rules_str': ['rule service name="ssh" accept',
                          'rule service name="http" accept']}
    assert 'tftp-client' not in get_used_services(conf, True)


def test_get_used_services_tuple_zone_negative():
    conf = (None, None, None, None, None,
            ['https'],  # conf[5], services
            None, None, None, None,
            ['dummy0'],  # conf[10], interfaces
            [],  # conf[11], sources
            [],  # conf[12], rules_str
            None, None, None)
    assert 'tftp-client' not in get_used_services_tuple(conf, True)

    conf = {'sources': ['10.1.2.0/24'],
            'rules_str': ['rule family="ipv4" source address="10.1.1.0/24" service name="ssh" reject'],
            'services': ['https']}
    conf = (None, None, None, None, None,
            ['https'],  # conf[5], services
            None, None, None, None,
            [],  # conf[10], interfaces
            ['10.1.2.0/24'],  # conf[11], sources
            ['rule family="ipv4" source address="10.1.1.0/24" service name="ssh" reject'],  # conf[12], rules_str
            None, None, None)
    assert 'tftp-client' not in get_used_services_tuple(conf, True)

    conf = (None, None, None, None, None,
            [],  # conf[5], services
            None, None, None, None,
            ['dummy0'],  # conf[10], interfaces
            ['fd00::/8'],  # conf[11], sources
            ['rule service name="ssh" accept', 'rule service name="http" accept'],  # conf[12], rules_str
            None, None, None)
    assert 'tftp-client' not in get_used_services_tuple(conf, True)


def test_get_used_services_policy():
    conf = {'services': ['tftp-client']}
    assert 'tftp-client' in get_used_services(conf, False)

    conf = {'rich_rules': ['rule family="ipv4" source address="10.1.1.0/24" service name="tftp-client" reject']}
    assert 'tftp-client' in get_used_services(conf, False)

    conf = {'rich_rules': ['rule service name="ssh" accept',
                           'rule service name="tftp-client" accept']}
    assert 'tftp-client' in get_used_services(conf, False)


def test_get_used_services_policy_negative():
    conf = {}
    assert 'tftp-client' not in get_used_services(conf, False)

    conf = {'services': []}
    assert 'tftp-client' not in get_used_services(conf, False)

    conf = {'services': ['ssh']}
    assert 'tftp-client' not in get_used_services(conf, False)

    conf = {'rich_rules': ['rule family="ipv4" source address="10.1.1.0/24" service name="http" reject']}
    assert 'tftp-client' not in get_used_services(conf, False)

    conf = {'rich_rules': ['rule service name="ssh" accept',
                           'rule service name="https" accept']}
    assert 'tftp-client' not in get_used_services(conf, False)
