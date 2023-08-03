from leapp.models import fields, Model, RPM
from leapp.topics import SystemInfoTopic
from leapp.utils.deprecation import deprecated


@deprecated(since='2023-08-03', message='The model has been deprecated in favour of InstalledTargetKernelInfo.')
class InstalledTargetKernelVersion(Model):
    """
    This message is used to propagate the version of the kernel that has been installed during the upgrade process.

    The version value is mainly used for boot loader entry manipulations, to know which boot entry to manipulate.
    """
    topic = SystemInfoTopic
    version = fields.String()


class KernelInfo(Model):
    """
    Information about the booted kernel.
    """
    topic = SystemInfoTopic

    pkg = fields.Model(RPM)
    """ Package providing the booted kernel. """

    uname_r = fields.String()
    """``uname -r`` of the booted kernel."""

    type = fields.StringEnum(['ordinary', 'realtime'], default='ordinary')
    # @FixMe(mhecko): I want to use kernel_lib.KernelType here, but I cannot import any library code (yet).
    # #               Figure out how to do it.


class InstalledTargetKernelInfo(Model):
    """Information about the installed target kernel."""
    topic = SystemInfoTopic

    pkg_nevra = fields.String()
    """Name, epoch, version, release, arch of the target kernel package."""

    uname_r = fields.String()
    """Kernel release of the target kernel."""

    kernel_img_path = fields.String()
    """Path to the vmlinuz kernel image stored in ``/boot``."""

    initramfs_path = fields.String()
    """Path to the initramfs image stored in ``/boot``."""
