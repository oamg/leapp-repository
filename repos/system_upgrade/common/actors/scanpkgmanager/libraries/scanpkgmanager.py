import os

from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.stdlib import api
from leapp.models import PkgManagerInfo


def _get_releasever_path():
    default_manager = 'yum' if get_source_major_version() == '7' else 'dnf'
    return '/etc/{}/vars/releasever'.format(default_manager)


def _releasever_exists(releasever_path):
    return os.path.isfile(releasever_path)


def get_etc_releasever():
    """ Get release version from "/etc/{yum,dnf}/vars/releasever" file """

    releasever_path = _get_releasever_path()
    if not _releasever_exists(releasever_path):
        return None

    with open(releasever_path, 'r') as fo:
        # we care about the first line only
        releasever = fo.readline().strip()

    return releasever


def process():
    api.produce(PkgManagerInfo(etc_releasever=get_etc_releasever()))
