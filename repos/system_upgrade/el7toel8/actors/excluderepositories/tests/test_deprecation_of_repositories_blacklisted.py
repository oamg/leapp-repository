import pytest

from leapp.models import RepositoriesBlacklisted
from leapp.utils.deprecation import _LeappDeprecationWarning


def test_deprecation_of_repositories_blacklisted():
    with pytest.warns(
        _LeappDeprecationWarning, match="Usage of deprecated Model"
    ):
        RepositoriesBlacklisted(repoids=["some repo id"])
