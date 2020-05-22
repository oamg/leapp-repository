import sys

import pytest

from leapp.models import InstalledRPM
from leapp.snactor.fixture import current_actor_context

no_yum = False
try:
    import yum
except ImportError:
    no_yum = True


@pytest.mark.skipif(
    sys.version_info.major >= 3,
    reason=(
        "There's no yum module for py3. The dnf module could have been used "
        "instead but there's a bug in dnf preventing us to do so: "
        "https://bugzilla.redhat.com/show_bug.cgi?id=1789840"
    ),
)
@pytest.mark.skipif(no_yum, reason="yum is unavailable")
def test_actor_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(InstalledRPM)
    assert current_actor_context.consume(InstalledRPM)[0].items
