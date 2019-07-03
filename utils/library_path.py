import logging
import sys

from leapp.repository.scan import find_and_scan_repositories


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, filename='/dev/null')
    logger = logging.getLogger('run_pytest.py')

    BASE_REPO = 'repos'
    repos = find_and_scan_repositories(BASE_REPO, include_locals=True)
    repos.load()

    print(','.join(repos.libraries))
