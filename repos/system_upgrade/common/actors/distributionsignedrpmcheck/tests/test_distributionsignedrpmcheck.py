from leapp import reporting
from leapp.libraries.actor import distributionsignedrpmcheck
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import RPM, ThirdPartyRPM

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


def test_actor_execution_without_third_party_pkgs(monkeypatch):
    third_party_rpm = ThirdPartyRPM(items=[])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[third_party_rpm]))
    monkeypatch.setattr(api, "show_message", lambda x: True)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    packages = distributionsignedrpmcheck.get_third_party_pkgs()

    assert not packages
    distributionsignedrpmcheck._generate_report(packages)
    assert reporting.create_report.called == 0


def test_actor_execution_with_third_party_pkgs(monkeypatch):
    installed_rpm = ThirdPartyRPM(
        items=[
            RPM(
                name="sample02",
                version="0.1",
                release="1.sm01",
                epoch="1",
                packager=RH_PACKAGER,
                arch="noarch",
                pgpsig="SOME_OTHER_SIG_X",
            ),
            RPM(
                name="sample04",
                version="0.1",
                release="1.sm01",
                epoch="1",
                packager=RH_PACKAGER,
                arch="noarch",
                pgpsig="SOME_OTHER_SIG_X",
            ),
            RPM(
                name="sample06",
                version="0.1",
                release="1.sm01",
                epoch="1",
                packager=RH_PACKAGER,
                arch="noarch",
                pgpsig="SOME_OTHER_SIG_X",
            ),
            RPM(
                name="sample08",
                version="0.1",
                release="1.sm01",
                epoch="1",
                packager=RH_PACKAGER,
                arch="noarch",
                pgpsig="SOME_OTHER_SIG_X",
            ),
        ]
    )
    monkeypatch.setattr(api, "current_actor", CurrentActorMocked(msgs=[installed_rpm]))
    monkeypatch.setattr(api, "show_message", lambda x: True)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    packages = distributionsignedrpmcheck.get_third_party_pkgs()
    assert len(packages) == 4
    distributionsignedrpmcheck._generate_report(packages)

    assert reporting.create_report.called == 1
    assert (
        "Packages not signed by the distribution vendor found on the system"
        in reporting.create_report.report_fields["title"]
    )
    # the key of the pre-generalization, original RHEL focused report
    assert (
        reporting.create_report.report_fields["key"]
        == "13f0791ae5f19f50e7d0d606fb6501f91b1efb2c"
    )
