from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class UdevAdmInfoData(Model):
    topic = SystemInfoTopic

    db = fields.String()
    """Database export obtained by executing 'udevadm info -e'."""
