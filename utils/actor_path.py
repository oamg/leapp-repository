import logging
import sys

from leapp.repository.scan import find_and_scan_repositories

def err_exit():
    # We want to be sure that `make test` (test_no_lint) will stop when expected
    # actor is not found and want to be sure that users will not overlook error
    # messages. This print will easily resolve the problem
    sys.stdout.write('ERROR:__read_error_messages_above_this_one_on_stderr__')
    sys.exit(1)

def main():
    logging.basicConfig(level=logging.INFO, filename='/dev/null')
    logger = logging.getLogger('run_pytest.py')

    BASE_REPO = 'repos'
    repos = find_and_scan_repositories(BASE_REPO, include_locals=True)
    repos.load()
    if len(sys.argv) > 1:
        actors = repos._lookup_actors(sys.argv[1])
        if not actors:
            sys.stderr.write('ERROR: No actor found for search "{}"\n'.format(sys.argv[1]))
            err_exit()
        print(' '.join([actor.full_path for actor in actors]))
    else:
        sys.stderr.write('ERROR: Missing commandline argument\n')
        err_exit()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # Make a generic exception as in case of error, without the explicit
        # sys.exit(1) call running of tests continues with all actors always
        # and we expect that many people will be affected unless they installed
        sys.stderr.write('ERROR: Unknown error: {}\n'.format(e))
        sys.stderr.write('ERROR: Possibly you need newer version of the leapp framework\n')
        sys.stderr.write('ERROR:   e.g.: rm -rf .tut && make install-deps-fedora\n')
        err_exit()
