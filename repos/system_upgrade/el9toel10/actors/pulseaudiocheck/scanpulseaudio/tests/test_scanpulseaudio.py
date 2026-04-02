import os

from leapp.libraries.actor import scanpulseaudio
from leapp.libraries.actor.scanpulseaudio import _get_dropin_dirs_with_content, _get_user_config_dirs, scan_pulseaudio


class TestGetDropinDirsWithContent:
    """Tests for _get_dropin_dirs_with_content."""

    def test_no_dropin_dirs(self, monkeypatch):
        monkeypatch.setattr(os.path, 'isdir', lambda _: False)
        assert _get_dropin_dirs_with_content() == []

    def test_empty_dropin_dirs(self, monkeypatch):
        monkeypatch.setattr(os.path, 'isdir', lambda _: True)
        monkeypatch.setattr(os, 'listdir', lambda _: [])
        assert _get_dropin_dirs_with_content() == []

    def test_dropin_dirs_with_content(self, monkeypatch):
        monkeypatch.setattr(os.path, 'isdir', lambda _: True)
        monkeypatch.setattr(os, 'listdir', lambda _: ['custom.conf'])
        result = _get_dropin_dirs_with_content()
        assert result == ['/etc/pulse/default.pa.d', '/etc/pulse/system.pa.d']

    def test_only_one_dropin_dir_exists(self, monkeypatch):
        monkeypatch.setattr(os.path, 'isdir', lambda path: path == '/etc/pulse/default.pa.d')
        monkeypatch.setattr(os, 'listdir', lambda _: ['custom.conf'])
        result = _get_dropin_dirs_with_content()
        assert result == ['/etc/pulse/default.pa.d']


class TestGetUserConfigDirs:
    """Tests for _get_user_config_dirs."""

    def test_no_user_config(self, monkeypatch):
        monkeypatch.setattr(os.path, 'isdir', lambda _: False)
        assert _get_user_config_dirs() == []

    def test_user_config_found(self, monkeypatch):
        monkeypatch.setattr(os.path, 'isdir', lambda path: path == '/home/testuser/.config/pulse')
        monkeypatch.setattr(os, 'listdir', lambda _: ['default.pa'])

        class FakeUser:
            pw_dir = '/home/testuser'

        monkeypatch.setattr(scanpulseaudio.pwd, 'getpwall', lambda: [FakeUser()])
        result = _get_user_config_dirs()
        assert result == ['/home/testuser/.config/pulse']


class TestScanPulseaudio:
    """Tests for scan_pulseaudio main function."""

    def test_no_custom_config(self, monkeypatch):
        monkeypatch.setattr(scanpulseaudio, '_check_default_configs_modified', lambda: [])
        monkeypatch.setattr(scanpulseaudio, '_get_dropin_dirs_with_content', lambda: [])
        monkeypatch.setattr(scanpulseaudio, '_get_user_config_dirs', lambda: [])

        result = scan_pulseaudio()

        assert result.modified_defaults == []
        assert result.dropin_dirs == []
        assert result.user_config_dirs == []

    def test_with_all_findings(self, monkeypatch):
        monkeypatch.setattr(scanpulseaudio, '_check_default_configs_modified',
                            lambda: ['/etc/pulse/daemon.conf'])
        monkeypatch.setattr(scanpulseaudio, '_get_dropin_dirs_with_content',
                            lambda: ['/etc/pulse/default.pa.d'])
        monkeypatch.setattr(scanpulseaudio, '_get_user_config_dirs',
                            lambda: ['/root/.config/pulse'])

        result = scan_pulseaudio()

        assert result.modified_defaults == ['/etc/pulse/daemon.conf']
        assert result.dropin_dirs == ['/etc/pulse/default.pa.d']
        assert result.user_config_dirs == ['/root/.config/pulse']
