import os

from leapp.libraries.stdlib import api
from leapp.models import (
    CopyFile,
    DracutModule,
    MultipathInfo,
    TargetUserSpaceUpgradeTasks,
    UpdatedMultipathConfig,
    UpgradeInitramfsTasks
)


def request_mpath_dracut_module_for_upgrade_initramfs():
    multipath_mod = DracutModule(name='multipath')
    request = UpgradeInitramfsTasks(include_dracut_modules=[multipath_mod])
    api.produce(request)


def request_mpath_confs(multipath_info):
    files_to_put_into_uspace = {  # source system path -> target uspace destination
        '/etc/multipath.conf': '/etc/multipath.conf'  # default config
    }

    if os.path.exists(multipath_info.config_dir):
        for filename in os.listdir(multipath_info.config_dir):
            config_path = os.path.join(multipath_info.config_dir, filename)
            if not config_path.endswith('.conf'):
                api.current_logger().debug(
                    'Skipping {} as it does not have .conf extension'.format(config_path)
                )
                continue
            files_to_put_into_uspace[config_path] = config_path

    for config_update in api.consume(UpdatedMultipathConfig):
        files_to_put_into_uspace[config_update.updated_config_location] = config_update.target_path

    # Note: original implementation would copy the /etc/multipath directory, which contains
    # /etc/multipath/conf.d location for drop-in files. The current logic includes it automatically,
    # if the user does not override this default location. In case that the default drop-in location
    # is changed, this new location is used.
    additional_files = ['/etc/xdrdevices.conf']
    for additional_file in additional_files:
        if os.path.exists(additional_file):
            files_to_put_into_uspace[additional_file] = additional_file

    copy_tasks = []
    for source_system_path, target_uspace_path in files_to_put_into_uspace.items():
        task = CopyFile(src=source_system_path, dst=target_uspace_path)
        copy_tasks.append(task)

    tasks = TargetUserSpaceUpgradeTasks(copy_files=copy_tasks)
    api.produce(tasks)


def process():
    multipath_info = next(api.consume(MultipathInfo), None)
    if not multipath_info:
        api.current_logger().debug(
            'Received no MultipathInfo message. No configfiles will '
            'be requested to be placed into target userspace.'
        )
        return
    request_mpath_confs(multipath_info)
    request_mpath_dracut_module_for_upgrade_initramfs()
