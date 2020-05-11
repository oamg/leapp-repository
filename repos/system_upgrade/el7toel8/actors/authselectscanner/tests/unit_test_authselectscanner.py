import textwrap

from mock import patch

from leapp.libraries.actor.authselectscanner import Authconfig, AuthselectScannerLibrary, DConf, read_file
from leapp.libraries.common.pam import PAM


def get_config(config):
    return textwrap.dedent(config).strip()


def test_read_file__non_existent():
    content = read_file('/this/does/not/exist')
    assert content == ''


def test_read_file__ok():
    content = read_file(__file__)
    assert content != ''
    assert 'test_read_file__ok' in content


def test_Authconfig_get_bool__non_existent():
    obj = Authconfig('')
    assert not obj.get_bool('non-existent-option')


def test_Authconfig_get_bool__true():
    obj = Authconfig(get_config('''
    test_a=True
    test_b=true
    test_c=Yes
    test_d=yes
    '''))

    assert obj.get_bool('test_a')
    assert obj.get_bool('test_b')
    assert obj.get_bool('test_c')
    assert obj.get_bool('test_d')


def test_Authconfig_get_bool__false():
    obj = Authconfig(get_config('''
    test_a=False
    test_b=false
    test_c=No
    test_d=no
    '''))

    assert not obj.get_bool('test_a')
    assert not obj.get_bool('test_b')
    assert not obj.get_bool('test_c')
    assert not obj.get_bool('test_d')


def test_Authconfig_get_string__non_existent():
    obj = Authconfig('')
    assert obj.get_string('non-existent-option') is None


def test_Authconfig_get_string__ok():
    obj = Authconfig(get_config('''
    test_a="str"
    test_b=str
    '''))

    assert obj.get_string('test_a') == 'str'
    assert obj.get_string('test_b') == 'str'


def test_DConf_get_bool__non_existent():
    obj = DConf('')
    assert not obj.get_bool('section', 'non-existent-option')


def test_DConf_get_bool__true():
    obj = DConf(get_config('''
    [section]
    test_a=True
    test_b=true
    test_c=Yes
    test_d=yes
    '''))

    assert obj.get_bool('section', 'test_a')
    assert obj.get_bool('section', 'test_b')
    assert obj.get_bool('section', 'test_c')
    assert obj.get_bool('section', 'test_d')


def test_DConf_get_bool__false():
    obj = DConf(get_config('''
    [section]
    test_a=False
    test_b=false
    test_c=No
    test_d=no
    '''))

    assert not obj.get_bool('section', 'test_a')
    assert not obj.get_bool('section', 'test_b')
    assert not obj.get_bool('section', 'test_c')
    assert not obj.get_bool('section', 'test_d')


def test_DConf_get_string__non_existent():
    obj = DConf('')
    assert obj.get_string('section', 'non-existent-option') is None


def test_DConf_get_string__ok():
    obj = DConf(get_config('''
    [section]
    test_a="str"
    test_b=str
    '''))

    assert obj.get_string('section', 'test_a') == 'str'
    assert obj.get_string('section', 'test_b') == 'str'


@patch('leapp.libraries.actor.authselectscanner.is_service_enabled')
def test_AuthselectScannerLibrary_step_detect_profile__None(mock_service):
    obj = AuthselectScannerLibrary([], Authconfig(''), DConf(''), PAM(''), '')
    mock_service.return_value = False
    assert obj.step_detect_profile() is None


@patch('leapp.libraries.actor.authselectscanner.is_service_enabled')
def test_AuthselectScannerLibrary_step_detect_profile__sssd(mock_service):
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = AuthselectScannerLibrary([], Authconfig(''), DConf(''), PAM(pam), '')
    mock_service.return_value = False
    assert obj.step_detect_profile() == 'sssd'


@patch('leapp.libraries.actor.authselectscanner.is_service_enabled')
def test_AuthselectScannerLibrary_step_detect_profile__winbind(mock_service):
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_winbind.so
    auth required pam_deny.so
    ''')

    obj = AuthselectScannerLibrary([], Authconfig(''), DConf(''), PAM(pam), '')
    mock_service.return_value = False
    assert obj.step_detect_profile() == 'winbind'


@patch('leapp.libraries.actor.authselectscanner.is_service_enabled')
def test_AuthselectScannerLibrary_step_detect_profile__nis(mock_service):
    pam = get_config('''
    auth sufficient pam_unix.so
    auth required pam_deny.so
    ''')

    obj = AuthselectScannerLibrary([], Authconfig(''), DConf(''), PAM(pam), '')
    mock_service.return_value = True
    assert obj.step_detect_profile() == 'nis'


@patch('leapp.libraries.actor.authselectscanner.is_service_enabled')
def test_AuthselectScannerLibrary_step_detect_profile__sssd_winbind(mock_service):
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_winbind.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = AuthselectScannerLibrary([], Authconfig(''), DConf(''), PAM(pam), '')
    mock_service.return_value = False
    assert obj.step_detect_profile() is None


@patch('leapp.libraries.actor.authselectscanner.is_service_enabled')
def test_AuthselectScannerLibrary_step_detect_profile__sssd_nis(mock_service):
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = AuthselectScannerLibrary([], Authconfig(''), DConf(''), PAM(pam), '')
    mock_service.return_value = True
    assert obj.step_detect_profile() is None


@patch('leapp.libraries.actor.authselectscanner.is_service_enabled')
def test_AuthselectScannerLibrary_step_detect_profile__winbind_nis(mock_service):
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_winbind.so
    auth required pam_deny.so
    ''')

    obj = AuthselectScannerLibrary([], Authconfig(''), DConf(''), PAM(pam), '')
    mock_service.return_value = True
    assert obj.step_detect_profile() is None


@patch('leapp.libraries.actor.authselectscanner.is_service_enabled')
def test_AuthselectScannerLibrary_step_detect_profile__sssd_winbind_nis(mock_service):
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_winbind.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = AuthselectScannerLibrary([], Authconfig(''), DConf(''), PAM(pam), '')
    mock_service.return_value = True
    assert obj.step_detect_profile() is None


def test_AuthselectScannerLibrary_step_detect_features__faillock():
    pam = get_config('''
    auth required pam_faillock.so preauth silent deny=4 unlock_time=1200
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = AuthselectScannerLibrary([], Authconfig(''), DConf(''), PAM(pam), '')
    assert obj.step_detect_features() == ['with-faillock']


def test_AuthselectScannerLibrary_step_detect_features__fingerprint():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth sufficient pam_fprintd.so
    auth required pam_deny.so
    ''')

    obj = AuthselectScannerLibrary([], Authconfig(''), DConf(''), PAM(pam), '')
    assert obj.step_detect_features() == ['with-fingerprint']


def test_AuthselectScannerLibrary_step_detect_features__access():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    account required pam_access.so
    ''')

    obj = AuthselectScannerLibrary([], Authconfig(''), DConf(''), PAM(pam), '')
    assert obj.step_detect_features() == ['with-pamaccess']


def test_AuthselectScannerLibrary_step_detect_features__mkhomedir():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    session optional pam_mkhomedir.so umask=0077
    ''')

    obj = AuthselectScannerLibrary([], Authconfig(''), DConf(''), PAM(pam), '')
    assert obj.step_detect_features() == ['with-mkhomedir']


def test_AuthselectScannerLibrary_step_detect_features__mkhomedir_oddjob():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    session optional pam_oddjob_mkhomedir.so umask=0077
    ''')

    obj = AuthselectScannerLibrary([], Authconfig(''), DConf(''), PAM(pam), '')
    assert obj.step_detect_features() == ['with-mkhomedir']


def test_AuthselectScannerLibrary_step_detect_features__all():
    pam = get_config('''
    auth required pam_faillock.so preauth silent deny=4 unlock_time=1200
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth sufficient pam_fprintd.so
    auth required pam_deny.so
    account required pam_access.so
    session optional pam_oddjob_mkhomedir.so umask=0077
    ''')

    obj = AuthselectScannerLibrary([], Authconfig(''), DConf(''), PAM(pam), '')
    features = obj.step_detect_features()
    assert len(features) == 4
    assert 'with-faillock' in features
    assert 'with-fingerprint' in features
    assert 'with-pamaccess' in features
    assert 'with-mkhomedir' in features


def test_AuthselectScannerLibrary_step_detect_sssd_features__sudo():
    nsswitch = get_config('''
    passwd:     files sss systemd
    group:      files sss systemd
    sudoers:    files sss
    ''')

    obj = AuthselectScannerLibrary(
        [], Authconfig(''), DConf(''), PAM(''), nsswitch
    )
    features = obj.step_detect_sssd_features('sssd')
    assert features == ['with-sudo']


def test_AuthselectScannerLibrary_step_detect_sssd_features__smartcard():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    ac = get_config('''
    USESMARTCARD=yes
    ''')

    obj = AuthselectScannerLibrary(
        [], Authconfig(ac), DConf(''), PAM(pam), ''
    )
    features = obj.step_detect_sssd_features('sssd')
    assert features == ['with-smartcard']


def test_AuthselectScannerLibrary_step_detect_sssd_features__smartcard_required():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    ac = get_config('''
    FORCESMARTCARD=yes
    ''')

    obj = AuthselectScannerLibrary(
        [], Authconfig(ac), DConf(''), PAM(pam), ''
    )
    features = obj.step_detect_sssd_features('sssd')
    assert features == ['with-smartcard-required']


def test_AuthselectScannerLibrary_step_detect_sssd_features__smartcard_lock():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    dconf = get_config('''
    [org/gnome/settings-daemon/peripherals/smartcard]
    removal-action='lock-screen'
    ''')

    obj = AuthselectScannerLibrary(
        [], Authconfig(''), DConf(dconf), PAM(pam), ''
    )
    features = obj.step_detect_sssd_features('sssd')
    assert features == ['with-smartcard-lock-on-removal']


def test_AuthselectScannerLibrary_step_detect_sssd_features__pkcs11():
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_pkcs11.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    ac = get_config('''
    USESMARTCARD=yes
    FORCESMARTCARD=yes
    ''')

    dconf = get_config('''
    [org/gnome/settings-daemon/peripherals/smartcard]
    removal-action='lock-screen'
    ''')

    obj = AuthselectScannerLibrary(
        [], Authconfig(ac), DConf(dconf), PAM(pam), ''
    )
    features = obj.step_detect_sssd_features('sssd')
    assert not features


def test_AuthselectScannerLibrary_step_detect_sssd_features__wrong_profile():
    nsswitch = get_config('''
    passwd:     files sss systemd
    group:      files sss systemd
    sudoers:    files sss
    ''')

    obj = AuthselectScannerLibrary(
        [], Authconfig(''), DConf(''), PAM(''), nsswitch
    )
    features = obj.step_detect_sssd_features('winbind')
    assert not features


def test_AuthselectScannerLibrary_step_detect_winbind_features__krb5():
    ac = get_config('''
    WINBINDKRB5=yes
    ''')

    obj = AuthselectScannerLibrary(
        [], Authconfig(ac), DConf(''), PAM(''), ''
    )
    features = obj.step_detect_winbind_features('winbind')
    assert features == ['with-krb5']


def test_AuthselectScannerLibrary_step_detect_winbind_features__wrong_profile():
    ac = get_config('''
    WINBINDKRB5=yes
    ''')

    obj = AuthselectScannerLibrary(
        [], Authconfig(ac), DConf(''), PAM(''), ''
    )
    features = obj.step_detect_winbind_features('sssd')
    assert not features


@patch('os.readlink')
@patch('os.path.islink')
@patch('os.path.isfile')
@patch('os.path.getmtime')
def test_AuthselectScannerLibrary_step_detect_if_confirmation_is_required__nosysconfig(
    mock_getmtime, mock_isfile, mock_islink, mock_readlink
):
    obj = AuthselectScannerLibrary(
        [], Authconfig(''), DConf(''), PAM(''), ''
    )
    mock_isfile.return_value = False
    assert obj.step_detect_if_confirmation_is_required()


@patch('os.readlink')
@patch('os.path.islink')
@patch('os.path.isfile')
@patch('os.path.getmtime')
def test_AuthselectScannerLibrary_step_detect_if_confirmation_is_required__nolink(
    mock_getmtime, mock_isfile, mock_islink, mock_readlink
):
    obj = AuthselectScannerLibrary(
        [], Authconfig(''), DConf(''), PAM(''), ''
    )
    mock_isfile.return_value = True
    mock_islink.return_value = False
    assert obj.step_detect_if_confirmation_is_required()


@patch('os.readlink')
@patch('os.path.islink')
@patch('os.path.isfile')
@patch('os.path.getmtime')
def test_AuthselectScannerLibrary_step_detect_if_confirmation_is_required__badlink(
    mock_getmtime, mock_isfile, mock_islink, mock_readlink
):
    obj = AuthselectScannerLibrary(
        [], Authconfig(''), DConf(''), PAM(''), ''
    )
    mock_isfile.return_value = True
    mock_islink.return_value = True
    mock_readlink.return_value = ''
    assert obj.step_detect_if_confirmation_is_required()


@patch('os.readlink')
@patch('os.path.islink')
@patch('os.path.isfile')
@patch('os.path.getmtime')
def test_AuthselectScannerLibrary_step_detect_if_confirmation_is_required__badmtime(
    mock_getmtime, mock_isfile, mock_islink, mock_readlink
):
    def my_getmtime(path):
        # Make sysconfig file older then other files.
        if path == '/etc/sysconfig/authconfig':
            return 100

        return 200

    obj = AuthselectScannerLibrary(
        [], Authconfig(''), DConf(''), PAM(''), ''
    )
    mock_isfile.return_value = True
    mock_islink.return_value = True
    mock_readlink.side_effect = '{}-ac'.format
    mock_getmtime.side_effect = my_getmtime
    assert obj.step_detect_if_confirmation_is_required()


@patch('os.readlink')
@patch('os.path.islink')
@patch('os.path.isfile')
@patch('os.path.getmtime')
def test_AuthselectScannerLibrary_step_detect_if_confirmation_is_required__pass(
    mock_getmtime, mock_isfile, mock_islink, mock_readlink
):
    def my_getmtime(path):
        # Make sysconfig file younger then other files.
        if path == '/etc/sysconfig/authconfig':
            return 200

        return 100

    obj = AuthselectScannerLibrary(
        [], Authconfig(''), DConf(''), PAM(''), ''
    )
    mock_isfile.return_value = True
    mock_islink.return_value = True
    mock_readlink.side_effect = '{}-ac'.format
    mock_getmtime.side_effect = my_getmtime
    assert not obj.step_detect_if_confirmation_is_required()


@patch('leapp.libraries.actor.authselectscanner.is_service_enabled')
@patch('leapp.libraries.actor.authselectscanner.AuthselectScannerLibrary.step_detect_if_confirmation_is_required')
def test_AuthselectScannerLibrary_process__simple(mock_confirm, mock_service):
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = AuthselectScannerLibrary(
        ['pam_unix', 'pam_sss', 'pam_deny'], Authconfig(''), DConf(''), PAM(pam), ''
    )
    mock_confirm.return_value = True
    mock_service.return_value = False
    authselect = obj.process()
    assert authselect.profile == 'sssd'
    assert not authselect.features
    assert authselect.confirm


@patch('leapp.libraries.actor.authselectscanner.is_service_enabled')
@patch('leapp.libraries.actor.authselectscanner.AuthselectScannerLibrary.step_detect_if_confirmation_is_required')
def test_AuthselectScannerLibrary_process__features(mock_confirm, mock_service):
    pam = get_config('''
    auth required pam_faillock.so preauth silent deny=4 unlock_time=1200
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    nsswitch = get_config('''
    passwd:     files sss systemd
    group:      files sss systemd
    sudoers:    files sss
    ''')

    obj = AuthselectScannerLibrary(
        ['pam_unix', 'pam_sss', 'pam_deny', 'pam_faillock'],
        Authconfig(''),
        DConf(''),
        PAM(pam),
        nsswitch
    )
    mock_confirm.return_value = True
    mock_service.return_value = False
    authselect = obj.process()
    assert authselect.profile == 'sssd'
    assert len(authselect.features) == 2
    assert 'with-faillock' in authselect.features
    assert 'with-sudo' in authselect.features
    assert authselect.confirm


@patch('leapp.libraries.actor.authselectscanner.is_service_enabled')
@patch('leapp.libraries.actor.authselectscanner.AuthselectScannerLibrary.step_detect_if_confirmation_is_required')
def test_AuthselectScannerLibrary_process__unknown_module(mock_confirm, mock_service):
    pam = get_config('''
    auth required pam_faillock.so preauth silent deny=4 unlock_time=1200
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = AuthselectScannerLibrary(
        ['pam_unix', 'pam_sss', 'pam_deny'],
        Authconfig(''),
        DConf(''),
        PAM(pam),
        ''
    )
    mock_confirm.return_value = True
    mock_service.return_value = False
    authselect = obj.process()
    assert authselect.profile is None
    assert not authselect.features
    assert authselect.confirm


@patch('leapp.libraries.actor.authselectscanner.is_service_enabled')
@patch('leapp.libraries.actor.authselectscanner.AuthselectScannerLibrary.step_detect_if_confirmation_is_required')
def test_AuthselectScannerLibrary_process__autoconfirm(mock_confirm, mock_service):
    pam = get_config('''
    auth sufficient pam_unix.so
    auth sufficient pam_sss.so
    auth required pam_deny.so
    ''')

    obj = AuthselectScannerLibrary(
        ['pam_unix', 'pam_sss', 'pam_deny'], Authconfig(''), DConf(''), PAM(pam), ''
    )
    mock_confirm.return_value = False
    mock_service.return_value = False
    authselect = obj.process()
    assert authselect.profile == 'sssd'
    assert not authselect.features
    assert not authselect.confirm
