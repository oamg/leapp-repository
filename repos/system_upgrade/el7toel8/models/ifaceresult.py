from leapp.models import Model, fields
from leapp.topics import NetworkInfoTopic


class IfacesInfo(Model):
    topic = NetworkInfoTopic
    if_name = fields.String()
    hwaddr = fields.String()
    driver = fields.String()
    ipv4addr = fields.String()
    bond_status = fields.String()
    bridge_status = fields.String()
    route_info = fields.String()


class IfaceResult(Model):
    topic = NetworkInfoTopic
    items = fields.List(fields.Model(IfacesInfo), default=[])
