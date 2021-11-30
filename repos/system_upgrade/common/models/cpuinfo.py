from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class CPUInfo(Model):
    """
    The model represents information about CPUs.

    The model currently doesn't represent all information about cpus could
    provide on the machine. Just part of them, in case any other attributes
    will be neded, the model can be extended.

    The provided info is aggregated - like from lscpu command. Expecting all
    CPUs are same on the machine (at least for now).
    """

    topic = SystemFactsTopic

    machine_type = fields.Nullable(fields.Integer())
    """
    Specifies machine type if provided.

    This is important for the check of s390x, whether the HW is supported
    by RHEL 8.
    """

    # TODO: regarding possible problems with LOCALE, I am keeping most of
    # parts commented out and focus just on the one particular needed info.
    # architecture = fields.String()
    # """ Architecture of the CPU (e.g. x86_64) """

    # byte_order = fields.StringEnum(['Little Endian', 'Big Endian'])
    # """ Byte order of the CPU: 'Little Endian' or 'Big Endian' """

    # flags = fields.List(fields.String(), default=[])
    # """ Specifies flags/features of the CPU. """

    # hypervisor = fields.Nullable(fields.String())
    # hypervisor_vendor = fields.Nullable(fields.String())

    # number = fields.Integer()
    # """ Number of CPUs. """

    # vendor_id = fields.Nullable(fields.String())
    # """ ID of vendor of the CPU. """

    # virtualization = fields.Nullable(fields.String())
    # virtualization_type = fields.Nullable(fields.String())
