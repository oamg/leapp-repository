import json
import os
import platform

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import EnvVar, IPUConfig, IPUSourceToPossibleTargets, OSRelease, Version

ENV_IGNORE = ('LEAPP_CURRENT_PHASE', 'LEAPP_CURRENT_ACTOR', 'LEAPP_VERBOSE',
              'LEAPP_DEBUG')

ENV_MAPPING = {'LEAPP_DEVEL_DM_DISABLE_UDEV': 'DM_DISABLE_UDEV'}


def get_env_vars():
    """
    Gather LEAPP_DEVEL environment variables and respective mappings to provide them as messages to be
    available after reboot.
    """
    env_vars = []
    leapp_vars = {k: v for (k, v) in os.environ.items() if k.startswith('LEAPP_') and k not in ENV_IGNORE}
    for k, v in leapp_vars.items():
        if k in ENV_MAPPING:
            env_vars.append(EnvVar(name=ENV_MAPPING.get(k), value=v))
            continue
        env_vars.append(EnvVar(name=k, value=v))

    return env_vars


def get_booted_kernel():
    """
    Get version and release of the currently used kernel in one string.
    """
    try:
        return run(['/usr/bin/uname', '-r'])['stdout'].strip()
    except CalledProcessError as e:
        raise StopActorExecutionError(
            message='Unable to obtain release of the booted kernel.',
            details={'details': str(e), 'stderr': e.stderr}
        )


def get_os_release(path):
    """
    Retrieve data about System OS release from provided file.

    :return: `OSRelease` model if the file can be parsed
    :raises: `IOError`
    """
    try:
        with open(path) as f:
            data = dict(l.strip().split('=', 1) for l in f.readlines() if '=' in l)
            return OSRelease(
                release_id=data.get('ID', '').strip('"'),
                name=data.get('NAME', '').strip('"'),
                pretty_name=data.get('PRETTY_NAME', '').strip('"'),
                version=data.get('VERSION', '').strip('"'),
                version_id=data.get('VERSION_ID', '').strip('"'),
                variant=data.get('VARIANT', '').strip('"') or None,
                variant_id=data.get('VARIANT_ID', '').strip('"') or None
            )
    except IOError as e:
        raise StopActorExecutionError(message='Cannot collect the system OS facts.',
                                      details={'details': str(e)})


def check_target_major_version(curr_version, target_version):
    required_major_version = int(curr_version.split('.')[0]) + 1
    specified_major_version = int(target_version.split('.')[0])
    if specified_major_version != required_major_version:
        raise StopActorExecutionError(
            message='Specified invalid major version of the target system',
            details={
                'Specified target major version': str(specified_major_version),
                'Required target major version': str(required_major_version),
                'hint': (
                    'The in-place upgrade is possible only to the next system'
                    ' major version: {ver}. Specify a valid version of the'
                    ' target system when running leapp.'
                    ' For more information about supported in-place upgrade paths'
                    ' follow: https://access.redhat.com/articles/4263361'
                    .format(ver=required_major_version)
                )
            }
        )


def load_upgrade_paths_definitions(paths_definition_file):
    with open(api.get_common_file_path(paths_definition_file)) as fp:
        definitions = json.loads(fp.read())
    return definitions


def load_raw_upgrade_paths_for_distro_and_flavour(distro_id, flavour, paths_definition_file='upgrade_paths.json'):
    all_definitions = load_upgrade_paths_definitions(paths_definition_file)
    raw_upgrade_paths_for_distro = all_definitions.get(distro_id, {})

    if not raw_upgrade_paths_for_distro:
        api.current_logger().warning('No upgrade paths defined for distro \'{}\''.format(distro_id))

    raw_upgrade_paths_for_flavour = raw_upgrade_paths_for_distro.get(flavour, {})

    if not raw_upgrade_paths_for_flavour:
        api.current_logger().warning('Cannot discover any upgrade paths for flavour: {}/{}'.format(distro_id, flavour))

    return raw_upgrade_paths_for_flavour


def construct_models_for_paths_matching_source_major(raw_paths, src_major_version):
    multipaths_matching_source = []
    for src_version, target_versions in raw_paths.items():
        if src_version.split('.')[0] == src_major_version:
            source_to_targets = IPUSourceToPossibleTargets(source_version=src_version,
                                                           target_versions=target_versions)
            multipaths_matching_source.append(source_to_targets)
    return multipaths_matching_source


def produce_ipu_config(actor):
    flavour = os.environ.get('LEAPP_UPGRADE_PATH_FLAVOUR')
    target_version = os.environ.get('LEAPP_UPGRADE_PATH_TARGET_RELEASE')
    os_release = get_os_release('/etc/os-release')
    source_version = os_release.version_id

    check_target_major_version(source_version, target_version)

    raw_upgrade_paths = load_raw_upgrade_paths_for_distro_and_flavour(os_release.release_id, flavour)
    source_major_version = source_version.split('.')[0]
    exposed_supported_paths = construct_models_for_paths_matching_source_major(raw_upgrade_paths, source_major_version)

    actor.produce(IPUConfig(
        leapp_env_vars=get_env_vars(),
        os_release=os_release,
        architecture=platform.machine(),
        version=Version(
            source=source_version,
            target=target_version
        ),
        kernel=get_booted_kernel(),
        flavour=flavour,
        supported_upgrade_paths=exposed_supported_paths
    ))
