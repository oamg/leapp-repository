from leapp import reporting
from leapp.libraries.actor.checkpulseaudio import check_pulseaudio
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, PulseAudioConfiguration, RPM


def _generate_rpm_with_name(name):
    """
    Generate new RPM model item with given name.

    :param name: rpm name
    :type name: str
    :return: new RPM object with name parameter set
    :rtype: RPM
    """
    return RPM(name=name,
               version='0.1',
               release='1.sm01',
               epoch='1',
               pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51',
               packager='Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>',
               arch='noarch')


class TestCheckPulseaudio:
    """Tests for check_pulseaudio checker function."""

    def test_pulseaudio_not_installed(self, monkeypatch):
        rpms = [_generate_rpm_with_name('some-other-package')]
        msg = PulseAudioConfiguration(modified_defaults=['/etc/pulse/daemon.conf'])
        curr_actor_mocked = CurrentActorMocked(msgs=[DistributionSignedRPM(items=rpms), msg])
        monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

        check_pulseaudio()

        assert not reporting.create_report.called

    def test_no_message(self, monkeypatch):
        rpms = [_generate_rpm_with_name('pulseaudio')]
        curr_actor_mocked = CurrentActorMocked(msgs=[DistributionSignedRPM(items=rpms)])
        monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

        check_pulseaudio()

        assert not reporting.create_report.called

    def test_no_custom_config(self, monkeypatch):
        rpms = [_generate_rpm_with_name('pulseaudio')]
        msg = PulseAudioConfiguration()
        curr_actor_mocked = CurrentActorMocked(msgs=[DistributionSignedRPM(items=rpms), msg])
        monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

        check_pulseaudio()

        assert not reporting.create_report.called

    def test_modified_defaults(self, monkeypatch):
        rpms = [_generate_rpm_with_name('pulseaudio')]
        msg = PulseAudioConfiguration(
            modified_defaults=['/etc/pulse/daemon.conf'],
        )
        curr_actor_mocked = CurrentActorMocked(msgs=[DistributionSignedRPM(items=rpms), msg])
        monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

        check_pulseaudio()

        assert reporting.create_report.called == 1
        report_fields = reporting.create_report.report_fields
        assert 'Custom PulseAudio configuration detected' in report_fields['title']
        assert '/etc/pulse/daemon.conf' in report_fields['summary']

    def test_dropin_dirs(self, monkeypatch):
        rpms = [_generate_rpm_with_name('pulseaudio')]
        msg = PulseAudioConfiguration(
            dropin_dirs=['/etc/pulse/default.pa.d'],
        )
        curr_actor_mocked = CurrentActorMocked(msgs=[DistributionSignedRPM(items=rpms), msg])
        monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

        check_pulseaudio()

        assert reporting.create_report.called == 1
        report_fields = reporting.create_report.report_fields
        assert '/etc/pulse/default.pa.d' in report_fields['summary']

    def test_user_config_dirs(self, monkeypatch):
        rpms = [_generate_rpm_with_name('pulseaudio')]
        msg = PulseAudioConfiguration(
            user_config_dirs=['/home/admin/.config/pulse'],
        )
        curr_actor_mocked = CurrentActorMocked(msgs=[DistributionSignedRPM(items=rpms), msg])
        monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

        check_pulseaudio()

        assert reporting.create_report.called == 1
        report_fields = reporting.create_report.report_fields
        assert '/home/admin/.config/pulse' in report_fields['summary']

    def test_report_all_sources(self, monkeypatch):
        rpms = [_generate_rpm_with_name('pulseaudio')]
        msg = PulseAudioConfiguration(
            modified_defaults=['/etc/pulse/daemon.conf'],
            dropin_dirs=['/etc/pulse/default.pa.d'],
            user_config_dirs=['/root/.config/pulse'],
        )
        curr_actor_mocked = CurrentActorMocked(msgs=[DistributionSignedRPM(items=rpms), msg])
        monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

        check_pulseaudio()

        assert reporting.create_report.called == 1
        report_fields = reporting.create_report.report_fields
        resources = report_fields['detail']['related_resources']
        pkg_resources = [r for r in resources if r['scheme'] == 'package']
        file_resources = [r for r in resources if r['scheme'] == 'file']
        assert len(pkg_resources) == 1
        assert pkg_resources[0]['title'] == 'pulseaudio'
        assert len(file_resources) == 3
