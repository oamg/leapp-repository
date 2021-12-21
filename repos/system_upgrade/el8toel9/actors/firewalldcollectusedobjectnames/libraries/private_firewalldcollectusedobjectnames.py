from leapp.models import FirewalldUsedObjectNames

try:
    from firewall.core.fw import Firewall
except ImportError:
    pass


def is_zone_in_use(conf):
    # This does not account for zone assignments given by NetworkManager.
    if conf.get('interfaces', []) or conf.get('sources', []):
        return True

    return False


def is_policy_in_use(conf, used_zones):
    # A policy is in use if both ingress_zones and egress_zones contain at
    # least one of following: an active zone, 'ANY', 'HOST'.
    for zone in conf.get('ingress_zones', []):
        if zone in ['ANY', 'HOST'] or zone in used_zones:
            break
    else:
        return False
    for zone in conf.get('egress_zones', []):
        if zone in ['ANY', 'HOST'] or zone in used_zones:
            return True
    return False


def get_used_services(conf, isZone):
    used_services = set()

    for service in conf.get('services', []):
        used_services.add(service)

    # Also need to look for 'service name="<service>"' in rich rules. The rule
    # strings are normalized by firewalld. zone keyword is 'rules_str'. policy
    # keyword is 'rich_rules'.
    for rule in conf.get('rules_str', []) if isZone else conf.get('rich_rules', []):
        try:
            search = 'service name="'
            start = rule.index(search) + len(search)
            stop = rule[start:].index('"')
            used_services.add(rule[start:start+stop])
        except ValueError:
            pass

    return used_services


def read_config():
    try:
        fw = Firewall(offline=True)
    except NameError:
        # import failure missing means firewalld is not installed. Just return
        # the defaults.
        return FirewalldUsedObjectNames()

    # This does not actually start firewalld. It just loads the configuration a
    # la firewall-offline-cmd.
    fw.start()

    # Default zone is always in use. Even without assigned interfaces/sources.
    used_zones = set([fw.get_default_zone()])
    for zone in fw.config.get_zones():
        obj = fw.config.get_zone(zone)
        conf = fw.config.get_zone_config_dict(obj)
        if is_zone_in_use(conf):
            used_zones.add(zone)

    used_policies = []
    for policy in fw.config.get_policy_objects():
        obj = fw.config.get_policy_object(policy)
        conf = fw.config.get_policy_object_config_dict(obj)
        if is_policy_in_use(conf, used_zones):
            used_policies.append(policy)

    used_services = set()
    for zone in fw.config.get_zones():
        obj = fw.config.get_zone(zone)
        conf = fw.config.get_zone_config_dict(obj)
        used_services.update(get_used_services(conf, True))
    for policy in fw.config.get_policy_objects():
        obj = fw.config.get_policy_object(policy)
        conf = fw.config.get_policy_object_config_dict(obj)
        used_services.update(get_used_services(conf, False))

    return FirewalldUsedObjectNames(zones=sorted(used_zones),
                                    policies=sorted(used_policies),
                                    services=sorted(used_services))
