import logging
import sys

from leapp.repository.scan import find_and_scan_repositories


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, filename='/dev/null')
    logger = logging.getLogger('run_pytest.py')

    BASE_REPO = 'repos'
    repos = find_and_scan_repositories(BASE_REPO, include_locals=True)
    repos.load()
    if len(sys.argv) > 1:
        actor = repos.lookup_actor(sys.argv[1])
        if actor:
            print(actor.full_path)
        else:
            sys.stdout.write('No actor found for search "{}"\n'.format(sys.argv[1]))
            sys.exit(1)
    else:
        sys.stdout.write('Missing commandline argument\n')
        sys.exit(1)
