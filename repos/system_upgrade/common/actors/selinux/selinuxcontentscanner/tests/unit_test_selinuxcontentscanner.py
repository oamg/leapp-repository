from leapp.libraries.actor import selinuxcontentscanner
from leapp.libraries.common.config import version
from leapp.libraries.stdlib import CalledProcessError


class run_mocked(object):
    def __init__(self):
        self.args = []
        self.called = 0

    def __call__(self, args, split=True):
        self.called += 1
        self.args = args

        if self.args == ['semodule', '-lfull']:
            stdout = ["400 permissive_abrt_t cil",
                      "400   zebra       cil",
                      "300 zebra       cil",
                      "100 vpn               pp  ",
                      "099 zebra             cil     ",
                      "100   minissdpd         pp"]

        elif self.args == ['semanage', 'export']:
            stdout = ["boolean -D",
                      "login -D",
                      "interface -D",
                      "user -D",
                      "port -D",
                      "node -D",
                      "fcontext -D",
                      "module -D",
                      "boolean -m -1 cron_can_relabel",
                      "port -a -t http_port_t -p udp 81",
                      "fcontext -a -f a -t httpd_sys_content_t '/web(/.*)?'",
                      "fcontext -a -f a -t cgdcbxd_exec_t '/ganesha(/.*)?'"]

        return {'stdout': stdout}


class run_mocked_fail(object):
    def __init__(self):
        self.called = 0

    def __call__(self, args, split=True):
        raise CalledProcessError(self, 1, "Mock error ;)")


def test_list_selinux_modules(monkeypatch):
    monkeypatch.setattr(selinuxcontentscanner, "run", run_mocked())

    assert selinuxcontentscanner.list_selinux_modules() == [
        ("permissive_abrt_t", "400"),
        ("zebra", "400"),
        ("zebra", "300"),
        ("vpn", "100"),
        ("zebra", "099"),
        ("minissdpd", "100"),
    ]

    monkeypatch.setattr(selinuxcontentscanner, "run", run_mocked_fail())

    assert selinuxcontentscanner.list_selinux_modules() == []


def test_get_selinux_customizations(monkeypatch):
    monkeypatch.setattr(version, "get_source_major_version", lambda: '8')
    monkeypatch.setattr(selinuxcontentscanner, "run", run_mocked())

    (semanage_valid, semanage_removed) = selinuxcontentscanner.get_selinux_customizations()

    assert len(semanage_valid) == 3
    assert semanage_valid[0] == "boolean -m -1 cron_can_relabel"
    assert semanage_valid[1] == "port -a -t http_port_t -p udp 81"
    assert semanage_valid[2] == "fcontext -a -f a -t httpd_sys_content_t '/web(/.*)?'"
    assert semanage_removed == ["fcontext -a -f a -t cgdcbxd_exec_t '/ganesha(/.*)?'"]
