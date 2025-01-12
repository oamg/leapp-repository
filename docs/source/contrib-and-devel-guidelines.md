# Contribution and development guidelines
## Code guidelines
### Retrieving information about the source system should be separated from its use
Leapp is an actor-based framework in which actor's communicate using messages.
New information extracted from the source system is often useful for other
actors developed in the future, and, therefore, extracted information should be
published (produced) as a message. The desired functionality---acting upon this
information---should be implemented as a standalone actor consuming the produced message.
Therefore, developing new features typically introduces at least two actors:
a _scanner_ that obtains the new information from the source system, and a _checker_
that consumes the message and acts upon it. Moreover, messages are recorded
in leapp's message database, allowing a post-mortem debugging.

### Actors need to be unit tested
Contributing code to someone else's codebase transfers the ownership to the
maintainers who will be maintaining your code. Therefore, the code should be
covered by unit tests that allow faster identification of (some) problems that
were unintentionally introduced. Tests also provide a useful window into how
you intend your code to be called, and witness the effort that have put into the
code, i.e., the code has been previously executed.

#### Testing tips
- Try avoiding the use of temporary files and directories. Instead, mock functions
provided by the os`/`shutil` libraries that are used by your actor whenever possible.

### Python2/3 compatibility
**Leapp is no longer released for RHEL 7, and thus, it is no longer necessary to maintain
Python2 compatibility in _common_ actors.**

Leapp allows users to upgrade from RHEL 7.9 (with Python 2.7) to newer RHEL releases.
At the same time, the upgrades from RHEL8, RHEL9, etc. are also supported. As actors
facilitating common functionality are shared between upgrade paths, one needs to write
common actors in way that is compatible with both, Python 2 and Python 3. There are a lot
of subtle changes in Python's standard library, however, there is typically no need to
check everything as when submitting a PR, end-to-end test will be run on a representative
subset of the supported upgrade paths. Typically, any incompatibilities would be
discovered either prior, or during execution of these tests.

### Reading environmental variables
Using environmental variables might be problematic as the computer is rebooted
several times during the upgrade process. The original environment does not
survive reboots. If you need to use environmental variables, use the prefix `LEAPP_`
in their name. Moreover, avoid using bare `os.environ` and instead use leapp's
`get_env` function. This combination ensures that the environmental variables
are available throughout the entire upgrade.

### Running external commands
Leapp provides the`stdlib.run` function to execute external commands in
its standard library. This function exposes a simple interface and ensures
that the calls are properly logged into the (pre)upgrade logs. Calling the function
might raise `CalledProcessError` (if the command exits with nonzero exit code; this
behaviour can be disabled). Calling the function can also rise `OSError`, if the
binary is not present, or if the file is not executable at all. The
`CalledProcessError` needs to be always handled. Handling `OSError` is not required,
given that the command is guaranteed to exist and be executable.

## Commits and pull requests
When your pull-request is ready to be reviewed, every commit needs to include
a title and a body continuing a description of the change --- what problem is
being solved and how. The end of the commit body should contain Jira issue
number (if applicable), GitHub issue that is being fixed, etc.:
```
  .... description ....
  Jira-ref: <ticket-number>
```

The granularity of commits depends strongly on the problem being solved. However,
a large number of small commits is typically undesired. If possible, aim a
Git history such that commits can be reverted individually, without requiring reverting
numerous other dependent commits in order to get the `main` branch into a working state.
