import os

import pytest

from leapp.libraries.actor import ntp2chrony

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

NTP_CONF = os.path.join(CUR_DIR, "data/ntp.conf")
STEP_TICKERS = os.path.join(CUR_DIR, "data/step_tickers")

# TODO [Artem] the following consts should use abs path as well.
#   reader of [[:digit:]]chrony.conf files does not support wildcards, so we
#   have to change the working directory here for now.
NTP_MATCH_DIR = "data/ntpconfs/"
CHRONY_MATCH_DIR = "data/chronyconfs/"


@pytest.fixture
def adjust_cwd():
    previous_cwd = os.getcwd()
    os.chdir(CUR_DIR)
    yield
    os.chdir(previous_cwd)


class TestConverter(object):
    def test_basic(self):
        config = ntp2chrony.NtpConfiguration(CUR_DIR, NTP_CONF, step_tickers=STEP_TICKERS)
        present = [config.restrictions, config.driftfile, config.trusted_keys, config.keys,
                   config.step_tickers, config.restrictions]
        for section in present:
            assert section
        chrony_conf = config.get_chrony_conf('/etc/chrony.keys')
        # additional verification section by section for each param in present?

        # verify step_tickers -> initstepslew
        initstepslew_line = next((l for l in chrony_conf.split('\n')
                                  if l.startswith('initstepslew')), None)
        assert initstepslew_line and initstepslew_line.endswith(' '.join(config.step_tickers))
        chrony_keys = config.get_chrony_keys()
        # verify keys generation
        for num, _, key in config.keys:
            expected = ('%(num)s MD5 %(key)s' %
                        {'key': 'HEX:' if len(key) > 20 else 'ASCII:' + key, 'num': num})
            # keys not from trusted keys are commented out by default
            if not any(num in range(x, y + 1) for (x, y) in config.trusted_keys):
                expected = '#' + expected
            assert expected in chrony_keys


class TestConfigConversion(object):
    def _do_match(self, expected_file, actual):
        expected_lines = []
        actual_lines = []
        with open(expected_file) as f:
            expected_lines = [l.strip() for l in f.readlines()
                              if l.strip() and not l.strip().startswith('#')]
        actual_lines = [l.strip() for l in actual.split('\n')
                        if l.strip() and not l.strip().startswith('#')]
        assert expected_lines == actual_lines

    def _check_existance(self, fname, default=''):
        if os.path.exists(fname):
            return fname
        return default

    def test_match(self, adjust_cwd):

        for f in [fe for fe in os.listdir(NTP_MATCH_DIR) if fe.endswith('conf')]:
            # get recorded actual result
            num = f.split('.')[0].split('_')[0]
            ntp_conf = os.path.join(NTP_MATCH_DIR, f)
            step_tickers = self._check_existance(
                os.path.join(NTP_MATCH_DIR, '%s_step_tickers' % num))
            config = ntp2chrony.NtpConfiguration('',
                                                 ntp_conf,
                                                 step_tickers=step_tickers)
            potential_chrony_keys = os.path.join(CHRONY_MATCH_DIR, "%s_chrony.keys" % num)
            actual_data = config.get_chrony_conf(chrony_keys_path=potential_chrony_keys)
            expected_fname = os.path.join(CHRONY_MATCH_DIR, "%s_chrony.conf" % num)
            # make sure recorded and generated configs match
            self._do_match(expected_fname, actual_data)
            actual_keys = config.get_chrony_keys()
            expected_keys_file = self._check_existance(potential_chrony_keys)
            # if keys are recorded or generated make sure they match
            if actual_keys and expected_keys_file != '':
                self._do_match(expected_keys_file, actual_keys)
