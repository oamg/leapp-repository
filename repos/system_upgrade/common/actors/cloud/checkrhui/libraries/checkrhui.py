import itertools
import os
from collections import namedtuple

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import rhsm, rhui
from leapp.libraries.common.config import version
from leapp.libraries.stdlib import api
from leapp.models import (
    CopyFile,
    DNFPluginTask,
    InstalledRPM,
    RHUIInfo,
    RpmTransactionTasks,
    TargetRHUIPostInstallTasks,
    TargetRHUIPreInstallTasks,
    TargetRHUISetupInfo,
    TargetUserSpacePreupgradeTasks
)

MatchingSetup = namedtuple('MatchingSetup', ['family', 'description'])


def into_set(pkgs):
    if isinstance(pkgs, set):
        return pkgs
    if isinstance(pkgs, str):
        return {pkgs}
    return set(pkgs)


def find_rhui_setup_matching_src_system(installed_pkgs, rhui_map):
    src_ver = version.get_source_major_version()
    arch = api.current_actor().configuration.architecture

    matching_setups = []
    for rhui_family, family_setups in rhui_map.items():
        if rhui_family.arch != arch:
            continue

        for setup in family_setups:
            if setup.os_version != src_ver:
                continue
            if setup.clients.issubset(installed_pkgs):
                matching_setups.append(MatchingSetup(family=rhui_family, description=setup))

    if not matching_setups:
        return None

    # In case that a RHUI variant uses a combination of clients identify the maximal client set
    matching_setups_by_size = sorted(matching_setups, key=lambda match: -len(match.description.clients))

    match = matching_setups_by_size[0]  # Matching setup with the highest number of clients
    if len(matching_setups) == 1:
        return match

    if len(matching_setups_by_size[0].description.clients) == len(matching_setups_by_size[1].description.clients):
        # Should not happen as no cloud providers use multi-client setups (at the moment)
        msg = 'Could not identify the source RHUI setup (ambiguous setup)'

        variant_detail_table = {
           rhui.RHUIVariant.ORDINARY: '',
           rhui.RHUIVariant.SAP: ' for SAP',
           rhui.RHUIVariant.SAP_APPS: ' for SAP Applications',
           rhui.RHUIVariant.SAP_HA: ' for SAP HA',
        }

        match0 = matching_setups_by_size[0]
        variant0_detail = variant_detail_table[match0.family.variant]
        clients0 = ' '.join(match0.description.clients)

        match1 = matching_setups_by_size[1]
        variant1_detail = variant_detail_table[match1.family.variant]
        clients1 = ' '.join(match1.description.clients)

        details = ('Leapp uses client-based identification of the used RHUI setup in order to determine what the '
                   'target RHEL content should be. According to the installed RHUI clients the system should be '
                   'RHEL {os_major}{variant0_detail} ({provider0}) (identified by clients {clients0}) but also '
                   'RHEL {os_major}{variant1_detail} ({provider1}) (identified by clients {clients1}).')
        details = details.format(os_major=version.get_source_major_version(),
                                 variant0_detail=variant0_detail, clients0=clients0, provider0=match0.family.provider,
                                 variant1_detail=variant1_detail, clients1=clients1, provider1=match1.family.provider)

        raise StopActorExecutionError(message=msg, details={'details': details})

    return match


def determine_target_setup_desc(cloud_map, rhui_family):
    variant_setups = cloud_map[rhui_family]
    target_major = version.get_target_major_version()

    for setup in variant_setups:
        if setup.os_version == target_major:
            return setup
    return None


def inhibit_if_leapp_pkg_to_access_target_missing(installed_pkgs, rhui_family, target_setup_desc):
    pkg_name = target_setup_desc.leapp_pkg

    if pkg_name not in installed_pkgs:
        summary = 'On {provider} the "{pkg}" is required to perform an in-place upgrade'
        summary = summary.format(provider=rhui_family.provider, pkg=pkg_name)
        reporting.create_report([
            reporting.Title('Package "{}" is not installed'.format(pkg_name)),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.RelatedResource('package', pkg_name),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.PUBLIC_CLOUD, reporting.Groups.RHUI]),
            reporting.Remediation(commands=[['yum', 'install', '-y', pkg_name]])
        ])
        return True
    return False


def stop_due_to_unknown_target_system_setup(rhui_family):
    msg = 'Failed to identify target RHUI setup'
    variant_detail = ' ({rhui_family.variant})' if rhui_family.variant != rhui.RHUIVariant.ORDINARY else ''
    details = ('Leapp successfully identified the current RHUI setup as a system provided by '
               '{provider}{variant_detail}, but it failed to determine'
               ' equivalent RHUI setup for the target OS.')
    details = details.format(provider=rhui_family.provider, variant_detail=variant_detail)
    raise StopActorExecutionError(message=msg, details={'details': details})


def customize_rhui_setup_for_gcp(rhui_family, setup_info):
    if not rhui_family.provider == rhui.RHUIProvider.GOOGLE:
        return

    # The google-cloud.repo repofile provides the repository containing the target clients. However, its repoid is the
    # same across all rhel versions, therefore, we need to remove the source google-cloud.repo to enable
    # correct target one.
    setup_info.preinstall_tasks.files_to_remove.append('/etc/yum.repos.d/google-cloud.repo')


def customize_rhui_setup_for_aws(rhui_family, setup_info):
    if rhui_family.provider != rhui.RHUIProvider.AWS:
        return

    target_version = version.get_target_major_version()
    if target_version == '8':
        return  # The rhel8 plugin is packed into leapp-rhui-aws as we need python2 compatible client

    amazon_plugin_copy_task = CopyFile(src='/usr/lib/python3.9/site-packages/dnf-plugins/amazon-id.py',
                                       dst='/usr/lib/python3.6/site-packages/dnf-plugins/')
    setup_info.postinstall_tasks.files_to_copy.append(amazon_plugin_copy_task)


def produce_rhui_info_to_setup_target(rhui_family, source_setup_desc, target_setup_desc):
    rhui_files_location = os.path.join(api.get_common_folder_path('rhui'), rhui_family.client_files_folder)

    files_to_access_target_client_repo = []
    for filename, target_path in target_setup_desc.mandatory_files:
        src_path = os.path.join(rhui_files_location, filename)
        files_to_access_target_client_repo.append(CopyFile(src=src_path, dst=target_path))

    for filename, target_path in target_setup_desc.optional_files:
        src_path = os.path.join(rhui_files_location, filename)

        if not os.path.exists(src_path):
            msg = "Optional file {} is present, will be used to setup target RHUI."
            api.current_logger().debug(msg.format(src_path))
            continue

        files_to_access_target_client_repo.append(CopyFile(src=src_path, dst=target_path))

    preinstall_tasks = TargetRHUIPreInstallTasks(files_to_copy_into_overlay=files_to_access_target_client_repo)

    files_supporting_client_operation = sorted(
        os.path.join(rhui_files_location, file) for file in target_setup_desc.files_supporting_client_operation
    )

    target_client_setup_info = TargetRHUISetupInfo(
        preinstall_tasks=preinstall_tasks,
        postinstall_tasks=TargetRHUIPostInstallTasks(),
        files_supporting_client_operation=files_supporting_client_operation
    )

    customize_rhui_setup_for_gcp(rhui_family, target_client_setup_info)
    customize_rhui_setup_for_aws(rhui_family, target_client_setup_info)

    rhui_info = RHUIInfo(
        provider=rhui_family.provider.lower(),
        variant=rhui_family.variant,
        src_client_pkg_names=sorted(source_setup_desc.clients),
        target_client_pkg_names=sorted(target_setup_desc.clients),
        target_client_setup_info=target_client_setup_info
    )
    api.produce(rhui_info)


def produce_rpms_to_install_into_target(source_setup, target_setup):
    to_install = sorted(target_setup.clients - source_setup.clients)
    to_remove = sorted(source_setup.clients - target_setup.clients)

    api.produce(TargetUserSpacePreupgradeTasks(install_rpms=sorted(target_setup.clients)))
    if to_install or to_remove:
        api.produce(RpmTransactionTasks(to_install=to_install, to_remove=to_remove))


def inform_about_upgrade_with_rhui_without_no_rhsm():
    if not rhsm.skip_rhsm():
        reporting.create_report([
            reporting.Title('Upgrade initiated with RHSM on public cloud with RHUI infrastructure'),
            reporting.Summary(
                'Leapp detected this system is on public cloud with RHUI infrastructure '
                'but the process was initiated without "--no-rhsm" command line option '
                'which implies RHSM usage (valid subscription is needed).'
            ),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Groups([reporting.Groups.PUBLIC_CLOUD]),
        ])
        return True
    return False


def process():
    installed_rpm = itertools.chain(*[installed_rpm_msg.items for installed_rpm_msg in api.consume(InstalledRPM)])
    installed_pkgs = {rpm.name for rpm in installed_rpm}

    src_rhui_setup = find_rhui_setup_matching_src_system(installed_pkgs, rhui.RHUI_SETUPS)
    if not src_rhui_setup:
        return
    api.current_logger().debug("The RHUI family of the source system is {}".format(src_rhui_setup.family))

    target_setup_desc = determine_target_setup_desc(rhui.RHUI_SETUPS, src_rhui_setup.family)

    if not target_setup_desc:
        # We know that we are on RHUI because we have identified what RHUI variant it is, but we don't know how does
        # the target system look like. Likely, our knowledge of what RHUI setups are there (RHUI_SETUPS) is incomplete.
        stop_due_to_unknown_target_system_setup(src_rhui_setup.family)
        return

    if inform_about_upgrade_with_rhui_without_no_rhsm():
        return

    if inhibit_if_leapp_pkg_to_access_target_missing(installed_pkgs, src_rhui_setup.family, target_setup_desc):
        return

    # Instruction on how to access the target content
    produce_rhui_info_to_setup_target(src_rhui_setup.family, src_rhui_setup.description, target_setup_desc)

    produce_rpms_to_install_into_target(src_rhui_setup.description, target_setup_desc)

    if src_rhui_setup.family.provider == rhui.RHUIProvider.AWS:
        # We have to disable Amazon-id plugin in the initramdisk phase as there is no network
        api.produce(DNFPluginTask(name='amazon-id', disable_in=['upgrade']))
