from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


class FirewallStatus(Model):
    topic = SystemFactsTopic

    enabled = fields.Boolean()
    active = fields.Boolean()


class FirewallsFacts(Model):
    topic = SystemFactsTopic

    firewalld = fields.Model(FirewallStatus)
    iptables = fields.Model(FirewallStatus)
    ip6tables = fields.Model(FirewallStatus)
