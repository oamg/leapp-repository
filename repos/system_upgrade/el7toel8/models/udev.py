from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class UdevAdmInfoData(Model):
    topic = SystemInfoTopic

    # Database export obtained by executing "udevadm info -e".
    db = fields.String()
