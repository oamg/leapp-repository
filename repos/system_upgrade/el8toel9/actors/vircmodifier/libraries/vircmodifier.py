from leapp.libraries.stdlib import api


def process(virc_messages):
    """
    Remove lines flagged by VircScanner from /etc/virc.
    """
    config = next(virc_messages, None)
    if list(virc_messages):
        api.current_logger().warning('Unexpectedly received more than one VircConfig message.')
    if not config or not config.lines_to_remove:
        return

    to_remove = set(config.lines_to_remove)

    try:
        with open(config.path, 'r') as f:
            lines = f.readlines()
    except (OSError, IOError) as error:
        api.current_logger().warning('Could not read {}: {}'.format(config.path, error))
        return

    filtered = [line for line in lines if line not in to_remove]

    try:
        with open(config.path, 'w') as f:
            f.writelines(filtered)
    except (OSError, IOError) as error:
        api.current_logger().warning('Could not write {}: {}'.format(config.path, error))
