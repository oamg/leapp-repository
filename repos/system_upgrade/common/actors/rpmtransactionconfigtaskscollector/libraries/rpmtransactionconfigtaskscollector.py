import os.path

from leapp.models import RpmTransactionTasks, InstalledRedHatSignedRPM
from leapp.libraries.stdlib import api


def load_tasks_file(path, logger):
    # Loads the given file and converts it to a deduplicated list of strings that are stripped
    if os.path.isfile(path):
        try:
            with open(path, 'r') as f:
                return list(
                    {entry.strip() for entry in f.read().split('\n') if entry.strip() and
                        not entry.strip().startswith('#')}
                )
        except IOError as e:
            logger.warning('Failed to open %s to load additional transaction data. Error: %s', path, str(e))
    return []


def load_tasks(base_dir, logger):
    # Loads configuration files to_install, to_keep, and to_remove from the given base directory
    rpms = next(api.consume(InstalledRedHatSignedRPM))
    rpm_names = [rpm.name for rpm in rpms.items]
    to_install = load_tasks_file(os.path.join(base_dir, 'to_install'), logger)
    # we do not want to put into rpm transaction what is already installed (it will go to "to_upgrade" bucket)
    to_install_filtered = [pkg for pkg in to_install if pkg not in rpm_names]

    filtered = set(to_install) - set(to_install_filtered)
    if filtered:
        api.current_logger().debug(
            'The following packages from "to_install" file will be ignored as they are already installed:'
            '\n- ' + '\n- '.join(filtered))

    return RpmTransactionTasks(
        to_install=to_install_filtered,
        to_keep=load_tasks_file(os.path.join(base_dir, 'to_keep'), logger),
        to_remove=load_tasks_file(os.path.join(base_dir, 'to_remove'), logger))
