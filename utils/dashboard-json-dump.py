from __future__ import print_function
import json

from leapp.utils.repository import find_repository_basedir
from leapp.repository.scan import find_and_scan_repositories

base_dir = find_repository_basedir('.')
repository = find_and_scan_repositories(base_dir, include_locals=True)

repository.load()

if not hasattr(repository, 'repos'):
    repository.repos = [repository]

print(json.dumps([repo.serialize() for repo in repository.repos]))
