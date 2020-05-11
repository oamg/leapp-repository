import os
import tempfile

import pytest

from leapp.libraries.actor import updateetcsysconfigkernel


# TODO [Artem] could be solved
@pytest.mark.skip(reason='Failing on CI complaining about missing leapp.db fiel')
def test_update_kernel_config(monkeypatch):
    temp = tempfile.NamedTemporaryFile(delete=False)
    with open('tests/files/original') as f:
        data = f.readlines()
        temp.writelines(data)
    temp.close()

    updateetcsysconfigkernel.update_kernel_config(temp.name)

    with open(temp.name) as f:
        result = f.readlines()

    with open('tests/files/expected') as f:
        expected = f.readlines()

    assert result == expected

    os.unlink(temp.name)
    assert not os.path.exists(temp.name)
