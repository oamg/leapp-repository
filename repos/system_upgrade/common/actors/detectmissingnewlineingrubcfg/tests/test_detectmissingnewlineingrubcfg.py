import pytest

from leapp.libraries.actor import detectmissingnewlineingrubcfg


@pytest.mark.parametrize(
    ('config_contents', 'error_detected'),
    [
        ('GRUB_DEFAULT=saved\nGRUB_DISABLE_SUBMENU=true\n', False),
        ('GRUB_DEFAULT=saved\nGRUB_DISABLE_SUBMENU=true', True)
    ]
)
def test_is_grub_config_missing_final_newline(monkeypatch, config_contents, error_detected):

    config_path = '/etc/default/grub'

    def mocked_get_config_contents(path):
        assert path == config_path
        return config_contents

    monkeypatch.setattr(detectmissingnewlineingrubcfg, '_get_config_contents', mocked_get_config_contents)

    assert detectmissingnewlineingrubcfg.is_grub_config_missing_final_newline(config_path) == error_detected
