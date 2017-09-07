from leapp.models import Model, fields
from leapp.topics import NetworkInfoTopic


class IfacesInfo(Model):
    topic = NetworkInfoTopic
    if_name = fields.String(required=True)
    hwaddr = fields.String(required=True)
    driver = fields.String(required=True)
    ipv4addr = fields.String(required=True)
    bond_status = fields.String(required=True)
    bridge_status = fields.String(required=True)
    route_info = fields.String(required=True)


class IfaceResult(Model):
    topic = NetworkInfoTopic
    items = fields.List(fields.Model(IfacesInfo), required=True, default=[])
