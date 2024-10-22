from leapp.models import FirewalldGlobalConfig

try:
    from firewall.core.fw import Firewall
except ImportError:
    pass


def as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value in ["no", "false"]:
            return False
        return True

    return False


def read_config():
    try:
        fw = Firewall(offline=True)
    except NameError:
        # import failure missing means firewalld is not installed. Just return
        # the defaults.
        return FirewalldGlobalConfig()

    # This does not actually start firewalld. It just loads the configuration a
    # la firewall-offline-cmd.
    fw.start()

    conf = fw.config.get_firewalld_conf()

    conf_dict = {}
    conf_dict['defaultzone'] = conf.get('DefaultZone')
    conf_dict['cleanuponexit'] = as_bool(conf.get('CleanupOnExit'))
    conf_dict['cleanupmodulesonexit'] = as_bool(conf.get('CleanupModulesOnExit'))
    conf_dict['ipv6_rpfilter'] = conf.get('IPv6_rpfilter')
    conf_dict['individualcalls'] = as_bool(conf.get('IndividualCalls'))
    conf_dict['logdenied'] = "off" if conf.get('LogDenied') in [None, "no"] else conf.get('LogDenied')
    conf_dict['firewallbackend'] = conf.get('FirewallBackend')
    conf_dict['flushallonreload'] = as_bool(conf.get('FlushAllOnReload'))
    conf_dict['reloadpolicy'] = conf.get('ReloadPolicy')
    conf_dict['rfc3964_ipv4'] = as_bool(conf.get('RFC3964_IPv4'))
    conf_dict['nftablesflowtable'] = conf.get('NftablesFlowtable')
    conf_dict['nftablescounters'] = as_bool(conf.get('NftablesCounters'))
    conf_dict['nftablestableowner'] = as_bool(conf.get('NftablesTableOwner'))

    # These have been removed in RHEL-10.
    #
    conf_dict['allowzonedrifting'] = False
    conf_dict['lockdown'] = False

    return FirewalldGlobalConfig(**conf_dict)
