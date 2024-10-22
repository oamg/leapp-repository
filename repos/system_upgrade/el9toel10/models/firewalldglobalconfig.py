from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class FirewalldGlobalConfig(Model):
    """
    The model contains firewalld global configuration. The configuration is
    usually located at /etc/firewalld/firewalld.conf.
    """
    topic = SystemInfoTopic

    # Defaults for RHEL-10.
    #
    defaultzone = fields.String(default='public')
    cleanuponexit = fields.Boolean(default=True)
    cleanupmodulesonexit = fields.Boolean(default=False)
    ipv6_rpfilter = fields.String(default='yes')
    individualcalls = fields.Boolean(default=False)
    logdenied = fields.String(default='off')
    firewallbackend = fields.String(default='nftables')
    flushallonreload = fields.Boolean(default=True)
    reloadpolicy = fields.String(default='INPUT:DROP,FORWARD:DROP,OUTPUT:DROP')
    rfc3964_ipv4 = fields.Boolean(default=True)
    nftablesflowtable = fields.String(default='off')
    nftablescounters = fields.Boolean(default=False)
    nftablestableowner = fields.Boolean(default=False)

    # These are deprecated and other values are ignored in RHEL-10.
    #
    allowzonedrifting = fields.Boolean(default=False)
    lockdown = fields.Boolean(default=False)
