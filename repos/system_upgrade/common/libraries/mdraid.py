import os

from leapp.libraries.stdlib import api, CalledProcessError, run


def is_mdraid_dev(dev):
    """
    Check if a given device is an md (Multiple Device) device

    It is expected that the "mdadm" command is available,
    if it's not it is assumed the device is not an md device.

    :return: True if the device is an md device, False otherwise
    :raises CalledProcessError: If an error occurred
    """
    fail_msg = 'Could not check if device "{}" is an md device: {}'
    if not os.path.exists('/usr/sbin/mdadm'):
        api.current_logger().warning(fail_msg.format(
            dev, '/usr/sbin/mdadm is not installed.'
        ))
        return False
    try:
        result = run(['mdadm', '--query', dev])
    except CalledProcessError as err:
        err.message = fail_msg.format(dev, err)
        raise  # let the calling actor handle the exception

    return '--detail' in result['stdout']


def get_component_devices(raid_dev):
    """
    Get list of component devices in an md (Multiple Device) array

    :return: The list of component devices or None in case of error
    :raises ValueError: If the device is not an mdraid device
    """
    try:
        # using both --verbose and --brief for medium verbosity
        result = run(['mdadm', '--detail', '--verbose', '--brief', raid_dev])
    except (OSError, CalledProcessError) as err:
        api.current_logger().warning(
            'Could not get md array component devices: {}'.format(err)
        )
        return None
    # example output:
    # ARRAY /dev/md0 level=raid1 num-devices=2 metadata=1.2 name=localhost.localdomain:0 UUID=c4acea6e:d56e1598:91822e3f:fb26832c # noqa: E501; pylint: disable=line-too-long
    #     devices=/dev/vda1,/dev/vdb1
    if 'does not appear to be an md device' in result['stdout']:
        raise ValueError("Expected md device, but got: {}".format(raid_dev))

    return sorted(result['stdout'].rsplit('=', 2)[-1].strip().split(','))
