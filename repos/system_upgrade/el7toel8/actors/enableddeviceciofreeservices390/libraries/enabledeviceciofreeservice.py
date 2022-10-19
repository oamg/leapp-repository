from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import SystemdServicesTasks


def process():
    if architecture.matches_architecture(architecture.ARCH_S390X):
        api.produce(SystemdServicesTasks(to_enable=['device_cio_free.service']))
