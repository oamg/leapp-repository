import os

from leapp.libraries.stdlib import api


def remove_log():
    filepath = '/var/log/upgrade.log'
    if os.path.isfile(filepath):
        api.current_logger().info('already exists a log file from a previous Leapp run, it will be removed')
        remove_file(filepath)


def remove_file(filepath):
    try:
        os.remove(filepath)
    except OSError as err:
        api.current_logger().error('Could not remove {0}: {1}.'.format(filepath, err))
