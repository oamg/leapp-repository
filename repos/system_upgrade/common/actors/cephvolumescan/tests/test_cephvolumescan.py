import pytest
from mock import Mock, patch

from leapp.libraries.actor import cephvolumescan
from leapp.models import InstalledRPM, LsblkEntry, RPM, StorageInfo
from leapp.reporting import Report

CONT_PS_COMMAND_OUTPUT = {
    "stdout":
    """CONTAINER ID IMAGE COMMAND CREATED STATUS PORTS NAMES
    b5a3d8ef25b9 undercloud-0.ctlplane.redhat.local:8787/rh-osbs/rhceph:5 "-n osd.8 -f --set..." \
        2 hours ago Up 2 hours ago ceph-bea1a933-0846-4aaa-8223-62cb8cb2873c-osd-8
    50d96fe72019 registry.redhat.io/rhceph/rhceph-4-rhel8:latest "/opt/ceph-contain..." \
        2 weeks ago Up 2 weeks ceph-osd-0
    f93c17b49c40 registry.redhat.io/rhceph/rhceph-4-rhel8:latest "/opt/ceph-contain..." \
        2 weeks ago Up 2 weeks ceph-osd-1
    0669880c52dc registry.redhat.io/rhceph/rhceph-4-rhel8:latest "/opt/ceph-contain..." \
        2 weeks ago Up 2 weeks ceph-mgr-ceph4-standalone
    d7068301294e registry.redhat.io/rhceph/rhceph-4-rhel8:latest "/opt/ceph-contain..." \
        2 weeks ago Up 2 weeks ceph-mon-ceph4-standalone
    63de6d00f241 registry.redhat.io/openshift4/ose-prometheus-alertmanager:4.1 "/bin/alertmanager..." \
        2 weeks ago Up 2 weeks alertmanager
    28ed65960c80 registry.redhat.io/rhceph/rhceph-4-dashboard-rhel8:4 "/run.sh" \
        2 weeks ago Up 2 weeks grafana-server
    f4b300d7a11f registry.redhat.io/openshift4/ose-prometheus-node-exporter:v4.1 "/bin/node_exporte..." \
        2 weeks ago Up 2 weeks node-exporter
    95a03700b3ff registry.redhat.io/openshift4/ose-prometheus:4.1 "/bin/prometheus -..." \
        2 weeks ago Up 2 weeks prometheus"""
    }

CEPH_VOLUME_OUTPUT = {
    "stdout": """{
        "0":[
            {
                "devices":[
                    "/dev/sda"
                ],
                "lv_name":"osd-block-c5215ba7-517b-45c7-88df-37a03eeaa0e9",
                "lv_uuid":"Tyc0TH-RDxr-ebAF-9mWF-Kh5R-YnvJ-cEcGVn",
                "tags":{
                    "ceph.encrypted":"1"
                },
                "type":"block",
                "vg_name":"ceph-a696c40d-6b1d-448d-a40e-fadca22b64bc"
            }
        ],
        "8":[
            {
                "devices": [
                    "/dev/nvme0n1"
                ],
                "lv_name": "osd-db-b04857a0-a2a2-40c3-a490-cbe1f892a76c",
                "lv_uuid": "zcvGix-drzz-JwzP-6ktU-Od6W-N5jL-kxRFa3",
                "tags":{
                    "ceph.encrypted":"1"
                },
                "type": "db",
                "vg_name": "ceph-b78309b3-bd80-4399-87a3-ac647b216b63"
            },
            {
                "devices": [
                    "/dev/sdb"
                ],
                "lv_name": "osd-block-477c303f-5eaf-4be8-b5cc-f6073eb345bf",
                "lv_uuid": "Mz1dep-D715-Wxh1-zUuS-0cOA-mKXE-UxaEM3",
                "tags":{
                    "ceph.encrypted":"1"
                },
                "type": "block",
                "vg_name": "ceph-e3e0345b-8be1-40a7-955a-378ba967f954"
            }
        ],
    }"""
}

CEPH_LVM_LIST = {
    '0': [{'devices': ['/dev/sda'],
           'lv_name': 'osd-block-c5215ba7-517b-45c7-88df-37a03eeaa0e9',
           'lv_uuid': 'Tyc0TH-RDxr-ebAF-9mWF-Kh5R-YnvJ-cEcGVn',
           'tags': {'ceph.encrypted': '1'},
           'type': 'block',
           'vg_name': 'ceph-a696c40d-6b1d-448d-a40e-fadca22b64bc'}],
    '1': [{'devices': ['/dev/nvme0n1'],
           'lv_name': 'osd-db-b04857a0-a2a2-40c3-a490-cbe1f892a76c',
           'lv_uuid': 'zcvGix-drzz-JwzP-6ktU-Od6W-N5jL-kxRFa3',
           'tags': {'ceph.encrypted': '1'},
           'type': 'block',
           'vg_name': 'ceph-b78309b3-bd80-4399-87a3-ac647b216b63'},
          {'devices': ['/dev/sdb'],
           'lv_name': 'osd-block-477c303f-5eaf-4be8-b5cc-f6073eb345bf',
           'lv_uuid': 'Mz1dep-D715-Wxh1-zUuS-0cOA-mKXE-UxaEM3',
           'tags': {'ceph.encrypted': '1'},
           'type': 'block',
           'vg_name': 'ceph-e3e0345b-8be1-40a7-955a-378ba967f954'}]
    }


@patch('leapp.libraries.actor.cephvolumescan.run')
def test_select_osd_container(m_run):

    m_run.return_value = CONT_PS_COMMAND_OUTPUT

    assert cephvolumescan.select_osd_container('docker') == "ceph-bea1a933-0846-4aaa-8223-62cb8cb2873c-osd-8"


@patch('leapp.libraries.actor.cephvolumescan.has_package')
@patch('leapp.libraries.actor.cephvolumescan.select_osd_container')
@patch('leapp.libraries.actor.cephvolumescan.run')
def test_get_ceph_lvm_list(m_run, m_osd_container, m_has_package):

    m_has_package.return_value = True
    m_osd_container.return_value = 'podman'
    m_run.return_value = CEPH_VOLUME_OUTPUT

    assert cephvolumescan.get_ceph_lvm_list() == CEPH_LVM_LIST


@patch('leapp.libraries.actor.cephvolumescan.os.path.isfile')
@patch('leapp.libraries.actor.cephvolumescan.get_ceph_lvm_list')
def test_encrypted_osds_list(m_get_ceph_lvm_list, m_isfile):

    m_get_ceph_lvm_list.return_value = CEPH_LVM_LIST
    m_isfile.return_value = True

    assert cephvolumescan.encrypted_osds_list() == [
        'Tyc0TH-RDxr-ebAF-9mWF-Kh5R-YnvJ-cEcGVn',
        'zcvGix-drzz-JwzP-6ktU-Od6W-N5jL-kxRFa3',
        'Mz1dep-D715-Wxh1-zUuS-0cOA-mKXE-UxaEM3'
    ]
