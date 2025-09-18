import json
import os
import platform

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import Distro, EnvVar, IPUConfig, IPUSourceToPossibleTargets, OSRelease, Version

ENV_IGNORE = ('LEAPP_CURRENT_PHASE', 'LEAPP_CURRENT_ACTOR', 'LEAPP_VERBOSE',
              'LEAPP_DEBUG')

ENV_MAPPING = {'LEAPP_DEVEL_DM_DISABLE_UDEV': 'DM_DISABLE_UDEV'}
CENTOS_VIRTUAL_VERSIONS_KEY = '_virtual_versions'


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


def get_virtual_version(all_upgrade_path_defs, distro, version):
    if distro.lower() != 'centos':
        return version

    centos_upgrade_paths = all_upgrade_path_defs.get('centos', {})
    if not centos_upgrade_paths:
        raise StopActorExecutionError('There are no upgrade paths defined for CentOS.')

    virtual_versions = centos_upgrade_paths.get(CENTOS_VIRTUAL_VERSIONS_KEY, {})
    if not virtual_versions:  # Unlikely, only if using old upgrade_paths.json, but the user should not touch the file
        details = {
            "details": "The file does not contain any information about virtual versions of CentOS"
        }
        raise StopActorExecutionError(
            "The internal upgrade_paths.json file is invalid.", details=details
        )

    virtual_version = virtual_versions.get(version)
    if not virtual_version:
        details = (
            'The {} field in upgrade path definitions for \'centos\' does not'
            ' provide any virtual version for version {}'
        ).format(CENTOS_VIRTUAL_VERSIONS_KEY, version)
        raise StopActorExecutionError(
            "Failed to identify virtual minor version number for the system.",
            details={"details": details},
        )
    return virtual_version


def extract_upgrade_paths_for_distro_and_flavour(all_definitions, distro, flavour):
    distro_paths = all_definitions.get(distro, {})
    if not distro_paths:
        api.current_logger().warning(
            "No upgrade paths defined for distro '{}'".format(distro)
        )

    distro_paths = distro_paths.get(flavour, {})
    if not distro_paths:
        api.current_logger().warning(
            "Cannot discover any upgrade paths for flavour: {}/{}".format(
                distro, flavour
            )
        )
    return distro_paths


def make_cross_distro_paths(all_paths, source_distro, target_distro, flavour):
    """
    Make paths for upgrade + conversion.

    :param all_paths: The raw upgrade paths retrieved from upgrade_paths.json
    :type all_paths: dict
    :param source_distro: The source distro.
    :type source_distro: str
    :param target_distro: The target distro.
    :type target_distro: str
    :param flavour: The flavour to find paths for.
    :type target_distro: str
    :return: A dictionary with conversion paths for upgrade + conversion between
             source and target distro.
    :rtype: dict
    """
    # using source and target for both distro and version gets confusing, using
    # a and b for distro instead
    paths_a = extract_upgrade_paths_for_distro_and_flavour(
        all_paths, source_distro, flavour
    )
    paths_b = extract_upgrade_paths_for_distro_and_flavour(
        all_paths, target_distro, flavour
    )

    conversion_paths = {}
    for source_ver_a, _ in paths_a.items():
        virt_source_ver_a = get_virtual_version(all_paths, source_distro, source_ver_a)

        for source_ver_b, target_ver_b in paths_b.items():
            virt_source_ver_b = get_virtual_version(all_paths, target_distro, source_ver_b)
            if virt_source_ver_a == virt_source_ver_b:
                conversion_paths[source_ver_a] = target_ver_b

    return conversion_paths


def construct_models_for_paths_matching_source_major(
    raw_paths, src_major_version
):
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
    target_distro = os.environ.get('LEAPP_TARGET_OS')

    check_target_major_version(source_version, target_version)

    all_upgrade_path_defs = load_upgrade_paths_definitions('upgrade_paths.json')
    raw_upgrade_paths = extract_upgrade_paths_for_distro_and_flavour(all_upgrade_path_defs,
                                                                     os_release.release_id,
                                                                     flavour)
    if os_release.release_id == target_distro:
        raw_upgrade_paths = extract_upgrade_paths_for_distro_and_flavour(
            all_upgrade_path_defs, os_release.release_id, flavour
        )
    else:
        raw_upgrade_paths = make_cross_distro_paths(
            all_upgrade_path_defs, os_release.release_id, target_distro, flavour
        )

    virtual_source_version = get_virtual_version(all_upgrade_path_defs, os_release.release_id, source_version)
    virtual_target_version = get_virtual_version(all_upgrade_path_defs, target_distro, target_version)

    source_major_version = source_version.split('.')[0]
    exposed_supported_paths = construct_models_for_paths_matching_source_major(
        raw_upgrade_paths, source_major_version
    )

    actor.produce(IPUConfig(
        leapp_env_vars=get_env_vars(),
        os_release=os_release,
        architecture=platform.machine(),
        version=Version(
            source=source_version,
            target=target_version,
            virtual_source_version=virtual_source_version,
            virtual_target_version=virtual_target_version,
        ),
        kernel=get_booted_kernel(),
        flavour=flavour,
        supported_upgrade_paths=exposed_supported_paths,
        distro=Distro(
            source=os_release.release_id,
            target=target_distro,
        ),
    ))
