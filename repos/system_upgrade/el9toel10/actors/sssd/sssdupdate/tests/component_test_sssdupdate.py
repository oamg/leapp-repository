import os
import pytest

from tempfile import NamedTemporaryFile

from leapp.models import SSSDConfig

def make_tmp_file(contents: str) -> NamedTemporaryFile:
    file = NamedTemporaryFile(mode='w+t', prefix='test.sssdupdate.', delete=False)
    file.write(contents)
    file.close()
    return file.name

def make_files(contents: list[str]) -> list[str]:
    files = []
    for conts in contents:
        files.append(make_tmp_file(conts))

    return files

def check_file(name:str, expected: str):
    with open(name, 'r') as f:
        assert f.read() == expected

@pytest.mark.parametrize('sssd', [(True), (False)])
def test_sssdupdate__no_change(current_actor_context, sssd: bool):
    contents = [
        """
        The time has come, the Walrus said,
        To talk of many things:
        Of shoes — and ships — and sealing-wax —
        Of cabbages — and kings —
        And why the sea is boiling hot —
        And whether pigs have wings.
        """,
        """
        Der Hölle Rache kocht in meinem Herzen,
        Tod und Verzweiflung flammet um mich her!
        Fühlt nicht durch dich Sarastro
        Todesschmerzen,
        So bist du meine Tochter nimmermehr.
        """
    ]

    files = make_files(contents)
    if sssd:
        config = SSSDConfig(sssd_config_files=files)
    else:
        config = SSSDConfig(ssh_config_files=files)

    current_actor_context.feed(config)
    current_actor_context.run()

    i = 0
    for file in files:
        check_file(file, contents[i])
        os.unlink(file)
        i += 1

def test_sssdupdate__sssd_change(current_actor_context):
    contents = [
        """
        [sssd]
        services = pam, nss
        domains = test
        """,
        """
        [sssd]
        # services = pam,nss
        domains = test
        """
    ]
    expected = [
        """
        [sssd]
        services = pam, nss,ssh
        domains = test
        """,
        """
        [sssd]
        # services = pam,nss,ssh
        domains = test
        """
    ]
    # A failure here indicates an error in the test
    assert len(contents) == len(expected)

    sssd_files = make_files(contents)
    ssh_files = []
    ssh_files.append(make_tmp_file(''))
    config = SSSDConfig(sssd_config_files=sssd_files, ssh_config_files = ssh_files)

    current_actor_context.feed(config)
    current_actor_context.run()

    os.unlink(ssh_files[0])
    i = 0
    for file in sssd_files:
        check_file(file, expected[i])
        os.unlink(file)
        i += 1

def test_sssdupdate__ssh_change(current_actor_context):
    contents = [
        """
        First line
        ProxyCommand  /usr/bin/sss_ssh_knownhostsproxy -p %p -d domain %h
        3rd line
        """,
        """
        #\tProxyCommand /usr/bin/sss_ssh_knownhostsproxy --port=%p  %h
        # Another comment
        """
    ]
    expected = [
        """
        First line
        KnownHostsCommand  /usr/bin/sss_ssh_knownhosts   -d domain %H
        3rd line
        """,
        """
        #\tKnownHostsCommand /usr/bin/sss_ssh_knownhosts   %H
        # Another comment
        """
    ]
    # A failure here indicates an error in the test
    assert len(contents) == len(expected)

    files = make_files(contents)
    config = SSSDConfig(ssh_config_files=files)

    current_actor_context.feed(config)
    current_actor_context.run()

    i = 0
    for file in files:
        check_file(file, expected[i])
        os.unlink(file)
        i += 1
