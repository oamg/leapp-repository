import pytest

from leapp.libraries.actor.sanebackendsmigrate import NEW_QUIRKS, update_sane

testdata = [
    {'sane-backends': '/etc/sane.d/canon_dr.conf'},
    {'sane-backends': ''},
    {'ble': ''}
]


class MockLogger(object):
    def __init__(self):
        self.debugmsg = ''
        self.errmsg = ''

    def debug(self, message):
        self.debugmsg += message

    def error(self, message):
        self.errmsg += message


class MockPackage(object):
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.config_content = ''


class MockPackageSet(object):
    def __init__(self):
        self.installed_packages = None

    def add_packages(self, pkgs):
        if self.installed_packages is None:
            self.installed_packages = []

        for rpm, config in pkgs.items():
            self.installed_packages.append(MockPackage(rpm, config))

    def is_installed(self, pkg):
        for rpm in self.installed_packages:
            if pkg == rpm.name:
                return True
        return False

    def append_content(self, path, content):
        found = False

        for rpm in self.installed_packages:
            if path == rpm.config:
                found = True
                rpm.config_content += content
        if not found:
            raise IOError('Error during writing to file: {}.'.format(path))

    def check_content(self, path, content):
        found = False

        for rpm in self.installed_packages:
            if path == rpm.config and content in rpm.config_content:
                found = True

        return found


class ExpectedOutput(object):
    def __init__(self):
        self.debugmsg = ''
        self.errmsg = ''

    def create(self, rpms):
        error_list = []
        found = False

        for pkg, config in rpms.items():
            if pkg == 'sane-backends':
                found = True
                break

        if found:
            for sane_config in NEW_QUIRKS.keys():
                self.debugmsg += ('Updating SANE configuration file {}.'
                                  .format(sane_config))
                if config == '' or config != sane_config:
                    error_list.append((sane_config,
                                       'Error during writing to file: {}.'
                                       .format(sane_config)))

        if error_list:
            self.errmsg = ('The files below have not been modified '
                           '(error message included):' +
                           ''.join(['\n    - {}: {}'.format(err[0], err[1])
                                   for err in error_list]))


@pytest.mark.parametrize("rpms", testdata)
def test_actor_check_report(rpms):
    logger = MockLogger()
    installed_packages = MockPackageSet()

    installed_packages.add_packages(rpms)

    expected = ExpectedOutput()
    expected.create(rpms)

    update_sane(logger.debug,
                logger.error,
                installed_packages.is_installed,
                installed_packages.append_content,
                installed_packages.check_content)

    assert expected.debugmsg == logger.debugmsg
    assert expected.errmsg == logger.errmsg
