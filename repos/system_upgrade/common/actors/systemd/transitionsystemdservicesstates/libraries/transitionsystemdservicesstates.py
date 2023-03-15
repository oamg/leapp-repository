from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import (
    SystemdServicesInfoSource,
    SystemdServicesInfoTarget,
    SystemdServicesPresetInfoSource,
    SystemdServicesPresetInfoTarget,
    SystemdServicesTasks
)

FMT_LIST_SEPARATOR = "\n    - "


def _get_desired_service_state(state_source, preset_source, preset_target):
    """
    Get the desired service state on the target system

    :param state_source: State on the source system
    :param preset_source: Preset on the source system
    :param preset_target: Preset on the target system
    :return: The desired state on the target system
    """

    if state_source in ("disabled", "enabled-runtime"):
        if preset_source == "disable":
            return preset_target + "d"  # use the default from target

    return state_source


def _get_desired_states(
    services_source, presets_source, services_target, presets_target
):
    "Get the states that services should be in on the target system"
    desired_states = {}

    for service in services_target:
        state_source = services_source.get(service.name)
        preset_target = _get_service_preset(service.name, presets_target)
        preset_source = _get_service_preset(service.name, presets_source)

        desired_state = _get_desired_service_state(
            state_source, preset_source, preset_target
        )
        desired_states[service.name] = desired_state

    return desired_states


def _get_service_task(service_name, desired_state, state_target, tasks):
    """
    Get the task to set the desired state of the service on the target system

    :param service_name: Then name of the service
    :param desired_state: The state the service should set to
    :param state_target: State on the target system
    :param tasks: The tasks to append the task to
    """
    if desired_state == state_target:
        return

    if desired_state == "enabled":
        tasks.to_enable.append(service_name)
    if desired_state == "disabled":
        tasks.to_disable.append(service_name)


def _get_service_preset(service_name, presets):
    preset = presets.get(service_name)
    if not preset:
        # shouldn't really happen as there is usually a `disable *` glob as
        # the last statement in the presets
        api.current_logger().debug(
            'No presets found for service "{}", assuming "disable"'.format(service_name)
        )
        return "disable"
    return preset


def _filter_services(services_source, services_target):
    """
    Filter out irrelevant services
    """
    filtered = []
    for service in services_target:
        if service.state not in ("enabled", "disabled", "enabled-runtime"):
            # Enabling/disabling of services is only relevant to these states
            continue

        state_source = services_source.get(service.name)
        if not state_source:
            # The service doesn't exist on the source system
            continue

        if state_source == "masked-runtime":
            # TODO(mmatuska): It's not possible to get the persistent
            # (non-runtime) state of a service with `systemctl`. One solution
            # might be to check symlinks
            api.current_logger().debug(
                'Skipping service in "masked-runtime" state: {}'.format(service.name)
            )
            continue

        filtered.append(service)

    return filtered


def _get_required_tasks(services_target, desired_states):
    """
    Get the required tasks to set the services on the target system to their desired state

    :return: The tasks required to be executed
    :rtype: SystemdServicesTasks
    """
    tasks = SystemdServicesTasks()

    for service in services_target:
        desired_state = desired_states[service.name]
        _get_service_task(service.name, desired_state, service.state, tasks)

    return tasks


def _report_kept_enabled(tasks):
    summary = (
        "Systemd services which were enabled on the system before the upgrade"
        " were kept enabled after the upgrade. "
    )
    if tasks:
        summary += (
            "The following services were originally disabled by preset on the"
            " upgraded system and Leapp attempted to enable them:{}{}"
        ).format(FMT_LIST_SEPARATOR, FMT_LIST_SEPARATOR.join(sorted(tasks.to_enable)))
        # TODO(mmatuska): When post-upgrade reports are implemented in
        # `setsystemdservicesstates actor, add a note here to check the reports
        # if the enabling failed

    reporting.create_report(
        [
            reporting.Title("Previously enabled systemd services were kept enabled"),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Groups([reporting.Groups.POST]),
        ]
    )


def _get_newly_enabled(services_source, desired_states):
    newly_enabled = []
    for service, state in desired_states.items():
        state_source = services_source[service]
        if state_source == "disabled" and state == "enabled":
            newly_enabled.append(service)

    return newly_enabled


def _report_newly_enabled(newly_enabled):
    summary = (
        "The following services were disabled before the upgrade and were set"
        "to enabled by a systemd preset after the upgrade:{}{}.".format(
            FMT_LIST_SEPARATOR, FMT_LIST_SEPARATOR.join(sorted(newly_enabled))
        )
    )

    reporting.create_report(
        [
            reporting.Title("Some systemd services were newly enabled"),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Groups([reporting.Groups.POST]),
        ]
    )


def _expect_message(model):
    """
    Get the expected message or throw an error
    """
    message = next(api.consume(model), None)
    if not message:
        raise StopActorExecutionError(
            "Expected {} message, but didn't get any".format(model.__name__)
        )
    return message


def process():
    services_source = _expect_message(SystemdServicesInfoSource).service_files
    services_target = _expect_message(SystemdServicesInfoTarget).service_files
    presets_source = _expect_message(SystemdServicesPresetInfoSource).presets
    presets_target = _expect_message(SystemdServicesPresetInfoTarget).presets

    services_source = {p.name: p.state for p in services_source}
    presets_source = {p.service: p.state for p in presets_source}
    presets_target = {p.service: p.state for p in presets_target}

    services_target = _filter_services(services_source, services_target)

    desired_states = _get_desired_states(
        services_source, presets_source, services_target, presets_target
    )
    tasks = _get_required_tasks(services_target, desired_states)

    api.produce(tasks)
    _report_kept_enabled(tasks)

    newly_enabled = _get_newly_enabled(services_source, desired_states)
    _report_newly_enabled(newly_enabled)
