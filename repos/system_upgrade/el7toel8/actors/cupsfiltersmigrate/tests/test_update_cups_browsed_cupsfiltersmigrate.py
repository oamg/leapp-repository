import pytest

from leapp.libraries.actor.cupsfiltersmigrate import BROWSED_CONFIG, update_cups_browsed

testdata = [
    {'cups-filters': '/etc/cups/cups-browsed.conf'},
    {'cups-filters': ''},
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

        for pkg, config in rpms.items():
            if pkg == 'cups-filters':
                self.debugmsg += 'Updating cups-browsed configuration file {}.'.format(BROWSED_CONFIG)
                if config == '':
                    error_list.append((BROWSED_CONFIG, 'Error during '
                                       'writing to file: {}.'.format(BROWSED_CONFIG)))

        if error_list:
            self.errmsg = ('The files below have not been modified '
                           '(error message included):' +
                           ''.join(['\n    - {}: {}'.format(err[0], err[1])
                                   for err in error_list]))


@pytest.mark.parametrize("rpms", testdata)
def test_update_cups_browsed(rpms):
    logger = MockLogger()
    installed_packages = MockPackageSet()

    installed_packages.add_packages(rpms)

    expected = ExpectedOutput()
    expected.create(rpms)

    update_cups_browsed(logger.debug,
                        logger.error,
                        installed_packages.is_installed,
                        installed_packages.append_content,
                        installed_packages.check_content)

    assert expected.debugmsg == logger.debugmsg
    assert expected.errmsg == logger.errmsg
