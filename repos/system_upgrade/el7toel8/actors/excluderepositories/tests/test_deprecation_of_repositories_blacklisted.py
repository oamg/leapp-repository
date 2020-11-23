import pytest

from leapp.models import RepositoriesBlacklisted


def test_deprecation_of_repositories_blacklisted():
    with pytest.deprecated_call(match="Usage of deprecated Model"):
        RepositoriesBlacklisted(repoids=["some repo id"])
