import sys

import pytest

from leapp.libraries.actor import rpmscanner
from leapp.libraries.common import module as module_lib
from leapp.libraries.common import rpms, testutils
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM, RPM
from leapp.snactor.fixture import current_actor_context

no_yum = False
try:
    import yum
except ImportError:
    no_yum = True

no_dnf = False
try:
    import dnf
except ImportError:
    no_dnf = True


# real module streams taken from Fedora 31
ARTIFACTS_AFTERBURN = [
    'afterburn-0:4.2.0-1.module_f31+6825+8330d585.x86_64',
    'afterburn-debuginfo-0:4.2.0-1.module_f31+6825+8330d585.x86_64',
    'rust-afterburn-0:4.2.0-1.module_f31+6825+8330d585.src',
    'rust-afterburn-debugsource-0:4.2.0-1.module_f31+6825+8330d585.x86_64'
]
ARTIFACTS_SUBVERSION_110 = [
    'mod_dav_svn-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'mod_dav_svn-debuginfo-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'python2-subversion-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'python2-subversion-debuginfo-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-0:1.10.6-1.module_f31+5204+aeb0fc0d.src',
    'subversion-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-debuginfo-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-debugsource-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-devel-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-devel-debuginfo-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-gnome-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-gnome-debuginfo-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-javahl-0:1.10.6-1.module_f31+5204+aeb0fc0d.noarch',
    'subversion-kde-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-kde-debuginfo-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-libs-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-libs-debuginfo-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-perl-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-perl-debuginfo-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-tools-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64',
    'subversion-tools-debuginfo-0:1.10.6-1.module_f31+5204+aeb0fc0d.x86_64'
]
ARTIFACTS_SUBVERSION_113 = [
    'mod_dav_svn-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'mod_dav_svn-debuginfo-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'python2-subversion-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'python2-subversion-debuginfo-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-0:1.13.0-1.module_f31+6955+7c448939.src',
    'subversion-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-debuginfo-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-debugsource-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-devel-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-devel-debuginfo-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-gnome-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-gnome-debuginfo-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-javahl-0:1.13.0-1.module_f31+6955+7c448939.noarch',
    'subversion-kde-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-kde-debuginfo-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-libs-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-libs-debuginfo-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-perl-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-perl-debuginfo-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-tools-0:1.13.0-1.module_f31+6955+7c448939.x86_64',
    'subversion-tools-debuginfo-0:1.13.0-1.module_f31+6955+7c448939.x86_64'
]


class ModuleMocked(object):
    def __init__(self, name, stream, artifacts):
        self.name = name
        self.stream = stream
        self.artifacts = artifacts

    def getName(self):
        return self.name

    def getStream(self):
        return self.stream

    def getArtifacts(self):
        return self.artifacts


MODULES = [
    ModuleMocked('afterburn', 'rolling', ARTIFACTS_AFTERBURN),
    ModuleMocked('subversion', '1.10', ARTIFACTS_SUBVERSION_110),
    ModuleMocked('subversion', '1.13', ARTIFACTS_SUBVERSION_113)
]


@pytest.mark.skipif(no_yum and no_dnf, reason='yum/dnf is unavailable')
def test_actor_execution(monkeypatch, current_actor_context):
    monkeypatch.setattr(rpmscanner.module_lib, 'get_modules', lambda: [])
    current_actor_context.run()
    assert current_actor_context.consume(InstalledRPM)
    assert current_actor_context.consume(InstalledRPM)[0].items


def test_map_modular_rpms_to_modules_empty(monkeypatch):
    monkeypatch.setattr(module_lib, 'get_modules', lambda: [])
    mapping = rpmscanner.map_modular_rpms_to_modules()
    assert not mapping


def test_map_modular_rpms_to_modules(monkeypatch):
    monkeypatch.setattr(module_lib, 'get_modules', lambda: MODULES)
    mapping = rpmscanner.map_modular_rpms_to_modules()
    assert mapping[
        ('afterburn', '0', '4.2.0', '1.module_f31+6825+8330d585', 'x86_64')
    ] == ('afterburn', 'rolling')
    assert mapping[
        ('subversion', '0', '1.10.6', '1.module_f31+5204+aeb0fc0d', 'x86_64')
    ] == ('subversion', '1.10')
    assert mapping[
        ('subversion', '0', '1.13.0', '1.module_f31+6955+7c448939', 'x86_64')
    ] == ('subversion', '1.13')
    assert not mapping.get(('subversion', '0', '1.13.0', '1.module_f31+6955+7c448939', 'noarch'))
    assert not mapping.get(('subversion', '0', '1.13.1', '1.module_f31+6955+7c448939', 'x86_64'))
    assert not mapping.get(('subversion', '1', '1.13.0', '1.module_f31+6955+7c448939', 'x86_64'))


INSTALLED_RPMS = [
    ('afterburn|4.2.0|1.module_f31+6825+8330d585|0|Fedora Project|x86_64|'
     'RSA/SHA256, Wed 16 Oct 2019 12:49:08 AM CEST, Key ID 50cb390b3c3359c4'),
    ('subversion|1.10.6|1.module_f31+5204+aeb0fc0d|0|Fedora Project|x86_64|'
     'RSA/SHA256, Thu 25 Jul 2019 01:41:52 PM CEST, Key ID 50cb390b3c3359c4'),
    # non-modular, epoch
    ('tcpdump|4.9.3|2.fc31|14|Fedora Project|x86_64|'
     'RSA/SHA256, Wed 22 Jul 2020 12:25:15 PM CEST, Key ID 50cb390b3c3359c4'),
    # non-modular, no epoch
    ('passwd|0.80|7.fc31|0|Fedora Project|x86_64|'
     'RSA/SHA256, Wed 04 Dec 2019 08:48:43 PM CET, Key ID 50cb390b3c3359c4')
]


PACKAGE_REPOS = {
    'afterburn': 'repo1',
    'subversion': 'repo2',
    'tcpdump': 'repo2'
}


def test_process(monkeypatch):
    monkeypatch.setattr(module_lib, 'get_modules', lambda: MODULES)
    monkeypatch.setattr(rpmscanner, 'get_package_repository_data', lambda: PACKAGE_REPOS)
    monkeypatch.setattr(rpms, 'get_installed_rpms', lambda: INSTALLED_RPMS)
    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())

    rpmscanner.process()
    assert api.produce.called
    assert len(api.produce.model_instances) == 1
    assert isinstance(api.produce.model_instances[0], InstalledRPM)
    items = {i.name: i for i in api.produce.model_instances[0].items}
    assert len(items) == 4

    assert items['afterburn'].epoch == '0'
    assert items['afterburn'].version == '4.2.0'
    assert items['afterburn'].release == '1.module_f31+6825+8330d585'
    assert items['afterburn'].arch == 'x86_64'
    assert items['afterburn'].module == 'afterburn'
    assert items['afterburn'].stream == 'rolling'

    assert items['subversion'].epoch == '0'
    assert items['subversion'].version == '1.10.6'
    assert items['subversion'].release == '1.module_f31+5204+aeb0fc0d'
    assert items['subversion'].arch == 'x86_64'
    assert items['subversion'].module == 'subversion'
    assert items['subversion'].stream == '1.10'

    assert items['tcpdump'].epoch == '14'
    assert items['tcpdump'].version == '4.9.3'
    assert items['tcpdump'].release == '2.fc31'
    assert items['tcpdump'].arch == 'x86_64'
    assert not items['tcpdump'].module
    assert not items['tcpdump'].stream

    assert items['passwd'].epoch == '0'
    assert items['passwd'].version == '0.80'
    assert items['passwd'].release == '7.fc31'
    assert items['passwd'].arch == 'x86_64'
    assert not items['passwd'].module
    assert not items['passwd'].stream
