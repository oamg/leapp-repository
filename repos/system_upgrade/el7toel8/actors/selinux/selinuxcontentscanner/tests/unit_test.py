from leapp.libraries.stdlib import run, CalledProcessError
from leapp.libraries.actor import library


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
                      "fcontext -a -f a -t ganesha_var_run_t '/ganesha(/.*)?'"]

        return {'stdout': stdout}


class run_mocked_fail(object):
    def __init__(self):
        self.called = 0

    def __call__(self, args, split=True):
        raise CalledProcessError(self, 1, "Mock error ;)")


def test_listSELinuxModules(monkeypatch):
    monkeypatch.setattr(library, "run", run_mocked())

    assert library.listSELinuxModules() == [("permissive_abrt_t", "400"),
                                            ("zebra", "400"),
                                            ("zebra", "300"),
                                            ("vpn", "100"),
                                            ("zebra", "099"),
                                            ("minissdpd", "100")]

    monkeypatch.setattr(library, "run", run_mocked_fail())

    assert library.listSELinuxModules() == []


def test_getSELinuxCustomizations(monkeypatch):
    monkeypatch.setattr(library, "run", run_mocked())

    (semanage_valid, semanage_removed) = library.getSELinuxCustomizations()

    assert len(semanage_valid) == 11
    assert semanage_valid[0] == "boolean -D"
    assert semanage_valid[10] == "fcontext -a -f a -t httpd_sys_content_t '/web(/.*)?'"
    assert semanage_removed == ["fcontext -a -f a -t ganesha_var_run_t '/ganesha(/.*)?'"]
