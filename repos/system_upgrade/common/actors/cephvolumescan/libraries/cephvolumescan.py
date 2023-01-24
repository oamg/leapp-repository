import json
import os
import re

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import InstalledRPM

CEPH_CONF = "/etc/ceph/ceph.conf"
CONTAINER = "ceph-osd"


def select_osd_container(engine):
    try:
        output = run([engine, 'ps'])
    except CalledProcessError as cpe:
        raise StopActorExecutionError(
            'Could not retrieve running containers list',
            details={'details': 'An exception raised during containers listing {}'.format(str(cpe))}
        )
    for line in output['stdout'].splitlines():
        container_name = line.split()[-1]
        if re.match(CONTAINER, container_name):
            return container_name
    return None


def get_ceph_lvm_list():
    base_cmd = ['ceph-volume', 'lvm', 'list', '--format', 'json']
    container_binary = 'podman' if has_package(InstalledRPM, 'podman') else \
        'docker' if has_package(InstalledRPM, 'docker') else ''
    if container_binary == '' and has_package(InstalledRPM, 'ceph-osd'):
        cmd_ceph_lvm_list = base_cmd
    elif container_binary == '':
        return None
    else:
        container_name = select_osd_container(container_binary)
        if container_name is None:
            return None
        cmd_ceph_lvm_list = [container_binary, 'exec', container_name]
        cmd_ceph_lvm_list.extend(base_cmd)
    try:
        output = run(cmd_ceph_lvm_list)
    except CalledProcessError as cpe:
        raise StopActorExecutionError(
            'Could not retrieve the ceph volumes list',
            details={'details': 'An exception raised while retrieving ceph volumes {}'.format(str(cpe))}
        )
    try:
        json_output = json.loads(output['stdout'])
    except ValueError as jve:
        raise StopActorExecutionError(
            'Could not load json file containing ceph volume list',
            details={'details': 'json file wrong format {}'.format(str(jve))}
        )
    return json_output


def encrypted_osds_list():
    result = []
    if os.path.isfile(CEPH_CONF):
        output = get_ceph_lvm_list()
        if output is not None:
            try:
                result = [output[key][0]['lv_uuid'] for key in output if output[key][0]['tags']['ceph.encrypted']]
            except KeyError:
                # TODO: possibly raise a report item with a medium risk factor
                # TODO: possibly create list of problematic osds, extend the cephinfo
                # #     model to include the list and then report it.
                api.current_logger().warning('ceph-osd is installed but no encrypted osd has been found')
    return result
