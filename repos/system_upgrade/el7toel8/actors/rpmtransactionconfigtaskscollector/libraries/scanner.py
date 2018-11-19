import os.path
from leapp.models import RpmTransactionTasks


def load_tasks_file(path, logger):
    # Loads the given file and converts it to a deduplicated list of strings that are stripped
    if os.path.isfile(path):
        try:
            with open(path, 'r') as f:
                return list(set([entry.strip() for entry in f.read().split() if entry.strip()]))
        except IOError as e:
            logger.warn('Failed to open %s to load additional transaction data. Error: %s', path, e.message)
    return []


def load_tasks(base_dir, logger):
    # Loads configuration files to_install, to_keep, and to_remove from the given base directory
    return RpmTransactionTasks(
            to_install=load_tasks_file(os.path.join(base_dir, 'to_install'), logger),
            to_keep=load_tasks_file(os.path.join(base_dir, 'to_keep'), logger),
            to_remove=load_tasks_file(os.path.join(base_dir, 'to_remove'), logger))

