import os

import pytest

from leapp.libraries.actor import copydnfconfintotargetuserspace
from leapp.libraries.common.testutils import logger_mocked, produce_mocked


@pytest.mark.parametrize(
    "userspace_conf_exists,expected",
    [(False, "/etc/dnf/dnf.conf"), (True, "/etc/leapp/files/dnf.conf")],
)
def test_copy_correct_dnf_conf(monkeypatch, userspace_conf_exists, expected):
    monkeypatch.setattr(os.path, "exists", lambda _: userspace_conf_exists)

    mocked_produce = produce_mocked()
    monkeypatch.setattr(copydnfconfintotargetuserspace.api, 'produce', mocked_produce)
    monkeypatch.setattr(copydnfconfintotargetuserspace.api, 'current_logger', logger_mocked())

    copydnfconfintotargetuserspace.process()

    assert mocked_produce.called == 1
    assert len(mocked_produce.model_instances) == 1
    assert len(mocked_produce.model_instances[0].copy_files) == 1
    assert mocked_produce.model_instances[0].copy_files[0].src == expected
    assert mocked_produce.model_instances[0].copy_files[0].dst == "/etc/dnf/dnf.conf"
