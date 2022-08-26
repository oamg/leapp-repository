from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class SystemdBrokenSymlinksSource(Model):
    """
    Information about broken systemd symlinks on the source system
    """

    topic = SystemInfoTopic
    broken_symlinks = fields.List(fields.String(), default=[])
    """
    List of broken systemd symlinks on the source system

    The values are absolute paths of the broken symlinks.
    """


class SystemdBrokenSymlinksTarget(SystemdBrokenSymlinksSource):
    """
    Analogy to :class:`SystemdBrokenSymlinksSource`, but for the target system
    """


class SystemdServicesTasks(Model):
    """
    Influence the systemd services of the target system

    E.g. it could be specified explicitly whether some services should
    be enabled or disabled after the in-place upgrade - follow descriptions
    of particular tasks for details.

    In case of conflicting tasks (e.g. the A service should be enabled and
    disabled in the same time):
       a) If conflicting tasks are detected during check phases,
          the upgrade is inhibited with the proper report.
       b) If conflicting tasks are detected during the final evaluation,
          error logs are created and such services will be disabled.
    """
    topic = SystemInfoTopic

    to_enable = fields.List(fields.String(), default=[])
    """
    List of systemd services to enable on the target system

    Masked services will not be enabled. Attempting to enable a masked service
    will be evaluated by systemctl as usually. The error will be logged and the
    upgrade process will continue.
    """

    to_disable = fields.List(fields.String(), default=[])
    """
    List of systemd services to disable on the target system
    """

    # NOTE: possible extension in case of requirement (currently not implemented):
    # to_unmask = fields.List(fields.String(), default=[])


class SystemdServiceFile(Model):
    """
    Information about single systemd service unit file

    This model is not expected to be produced nor consumed by actors directly.
    See the :class:`SystemdServicesInfoSource` and :class:`SystemdServicesPresetInfoTarget`
    for more info.
    """
    topic = SystemInfoTopic

    name = fields.String()
    """
    Name of the service unit file
    """

    state = fields.StringEnum([
        'alias',
        'bad',
        'disabled',
        'enabled',
        'enabled-runtime',
        'generated',
        'indirect',
        'linked',
        'linked-runtime',
        'masked',
        'masked-runtime',
        'static',
        'transient',
    ])
    """
    The state of the service unit file
    """


class SystemdServicesInfoSource(Model):
    """
    Information about systemd services on the source system
    """
    topic = SystemInfoTopic

    service_files = fields.List(fields.Model(SystemdServiceFile), default=[])
    """
    List of all installed systemd service unit files

    Instances of service template unit files don't have a unit file
    and therefore aren't included, but their template files are.
    Generated service unit files are also included.
    """


class SystemdServicesInfoTarget(SystemdServicesInfoSource):
    """
    Analogy to :class:`SystemdServicesInfoSource`, but for the target system

    This information is taken after the RPM Upgrade and might become
    invalid if there are actors calling systemctl enable/disable directly later
    in the upgrade process. Therefore it is recommended to use
    :class:`SystemdServicesTasks` to alter the state of units in the
    FinalizationPhase.
    """


class SystemdServicePreset(Model):
    """
    Information about a preset for systemd service
    """

    topic = SystemInfoTopic
    service = fields.String()
    """
    Name of the service, with the .service suffix
    """

    state = fields.StringEnum(['disable', 'enable'])
    """
    The state set by a preset file
    """


class SystemdServicesPresetInfoSource(Model):
    """
    Information about presets for systemd services
    """
    topic = SystemInfoTopic

    presets = fields.List(fields.Model(SystemdServicePreset), default=[])
    """
    List of all service presets
    """


class SystemdServicesPresetInfoTarget(SystemdServicesPresetInfoSource):
    """
    Analogy to :class:`SystemdServicesPresetInfoSource` but for the target system
    """
