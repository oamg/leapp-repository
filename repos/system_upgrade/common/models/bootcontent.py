from leapp.models import Model, fields
from leapp.topics import BootPrepTopic


class BootContent(Model):
    """
    For information about what Leapp copies to the /boot/. We need to pass this information
    at least to the actors performing /boot/ cleanup.
    """
    topic = BootPrepTopic

    kernel_path = fields.String(help='Filepath of the kernel copied to /boot/ by Leapp.')
    initram_path = fields.String(help='Filepath of the initramfs copied to /boot/ by Leapp.')
