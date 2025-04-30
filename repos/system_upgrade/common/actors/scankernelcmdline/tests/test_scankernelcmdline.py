import pytest

from leapp.libraries.actor import scankernelcmdline
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import KernelCmdline, KernelCmdlineArg


def mock_cmd_output():
    expected_cmd_output = (
        'BOOT_IMAGE=(hd0,msdos1)/vmlinuz-xxx root=UUID=some_uid ro console=tty0'
        ' console=ttyS0,115200 rd_NO_PLYMOUTH biosdevname=0 net.ifnames=0 crashkernel=auto'
        )
    return expected_cmd_output


def test_cmdline_output(monkeypatch):

    monkeypatch.setattr(scankernelcmdline, 'get_cmdline_input', mock_cmd_output)
    current_actor = CurrentActorMocked(src_ver='8.10', dst_ver='9.6')
    monkeypatch.setattr(api, 'current_actor', current_actor)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scankernelcmdline.parse_cmdline_input()

    expected_params = [KernelCmdlineArg(key=k, value=v) for k, v in [
        ('BOOT_IMAGE', '(hd0,msdos1)/vmlinuz-xxx'),
        ('root', 'UUID=some_uid'),
        ('ro', None),
        ('console', 'tty0'),
        ('console', 'ttyS0,115200'),
        ('rd_NO_PLYMOUTH', None),
        ('biosdevname', '0'),
        ('net.ifnames', '0'),
        ('crashkernel', 'auto')]]

    expected_output_msg = KernelCmdline(parameters=expected_params)
    assert api.produce.model_instances
    assert expected_output_msg == api.produce.model_instances[0]


def test_cmdline_content(monkeypatch):

    def run_mocked(cmd, **kwargs):
        assert cmd == ['cat', '/proc/cmdline']
        output = mock_cmd_output()
        return {'stdout': output}

    monkeypatch.setattr(scankernelcmdline, 'run', run_mocked)
    cmd_output = scankernelcmdline.get_cmdline_input()
    expected_cmd_output = mock_cmd_output()

    assert cmd_output == expected_cmd_output


@pytest.mark.parametrize('is_os_error', [True, False])
def test_cmdline_run_failed(monkeypatch, is_os_error):

    def run_mocked_error(cmd, **kwargs):
        assert cmd == ['cat', '/proc/cmdline']
        if is_os_error:
            raise OSError('OSError raised')
        raise CalledProcessError("CalledProcessError raised", cmd, "result")

    monkeypatch.setattr(scankernelcmdline, 'run', run_mocked_error)
    cmd_output = scankernelcmdline.get_cmdline_input()
    assert cmd_output == ''
