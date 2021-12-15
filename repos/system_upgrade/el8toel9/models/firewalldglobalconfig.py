from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class FirewalldGlobalConfig(Model):
    """
    The model contains firewalld global configuration. The configuration is
    usually located at /etc/firewalld/firewalld.conf.
    """
    topic = SystemInfoTopic

    # Defaults for RHEL-9.
    #
    defaultzone = fields.String(default='public')
    cleanuponexit = fields.Boolean(default=True)
    cleanupmodulesonexit = fields.Boolean(default=False)
    lockdown = fields.Boolean(default=False)
    ipv6_rpfilter = fields.Boolean(default=True)
    individualcalls = fields.Boolean(default=False)
    logdenied = fields.String(default='off')
    firewallbackend = fields.String(default='nftables')
    flushallonreload = fields.Boolean(default=True)
    rfc3964_ipv4 = fields.Boolean(default=True)

    # These have been removed in RHEL-9.
    #
    allowzonedrifting = fields.Boolean(default=False)
