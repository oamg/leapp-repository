# Coding guidelines

Your code should follow the [Python Coding Guidelines](https://leapp.readthedocs.io/en/latest/contributing.html#follow-python-coding-guidelines) used for the leapp project. On top of these rules follow instructions
below.

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

Also note that **interaction with the system during the `CheckPhase` phase is
prohibited** in this project. This means that RW operations from/to any file
or execution shell commands is not allowed in this phase.

### Actors need to be unit tested
Contributing code to someone else's codebase transfers the ownership to the
maintainers who will be maintaining your code. Therefore, the code should be
covered by unit tests that allow faster identification of (some) problems that
were unintentionally introduced. Tests also provide a useful window into how
you intend your code to be called, and witness the effort that have put into the
code, i.e., the code has been previously executed.

#### Testing tips
- Try avoiding the use of temporary files and directories. Instead, mock functions
provided by the {py:mod}`os`/{py:mod}`shutil` libraries that are used by your actor whenever possible.
- Check unit-tests in other actors to get inspiration
- Use the `leapp.libraries.common.testutils` library when in tests when possible.
  It contains various useful functions and classes that makes your testing much
  easier.

### Python compatibility
**We are stopping support of RHEL 7 in this project, and thus, it is no longer
necessary to maintain Python2 compatibility in _common_ actors.**

Leapp repositories in this project allows in-place upgrade between major versions
of RHEL (and with some changes also RHEL-like) systems. As each system major
version has a different platform Python, actors have to be written in way that
code is compatible with both, the source and the target system's Python.

As actors facilitating common functionality are shared between upgrade paths,
such actors must be compatible across all _system_ Python versions where they
can be used.

Here is the list of repositories in this project with the Python compatibility
requirements:
* `system_upgrade/common` - 3.6, 3.9, 3.12 (_you can start to ignore Python 2.7_)
* `system_upgrade/el8toel9` - 3.6, 3.9
* `system_upgrade/el9toel10` - 3.9, 3.12

Pay attention to linters to discover possible problems. Also, correctly written
unit-tests can help you to discover potential problems in actors between different
versions of python. Note that we execute unit-tests for each leapp repository
in this project for each relevant version of Python.

### Reading environmental variables
Using environmental variables might be problematic as the computer is rebooted
several times during the upgrade process. The original environment does not
survive reboots. If you need to use environmental variables, use the prefix `LEAPP_`
in their name. Moreover, avoid using bare {py:data}`os.environ` and instead use provided
`get_env` function from the `leapp.libraries.common.config` library.
This combination ensures that the environmental variables are available
throughout the entire upgrade and also helps with possible investigation when
any problems occur.

### Running external commands
Leapp provides the {py:func}`leapp.libraries.stdlib.run` function to execute
external commands in its standard library. This function exposes a simple
interface and ensures that the calls are properly logged. Calling the function
might raise {py:exc}`leapp.libraries.stdlib.CalledProcessError` (if the command
exits with nonzero exit code; this behaviour can be disabled). Calling the
function can also raise {py:exc}`OSError`, if the binary is not present, or if
the file is not executable at all. The
{py:exc}`~leapp.libraries.stdlib.CalledProcessError` needs to be always
handled. Handling {py:exc}`OSError` is not required if the application is
guaranteed to exist and executable.

The use of the {py:mod}`subprocess` library is forbidden in leapp repositories.
Use of the library would require very good reasoning, why the
{py:func}`~leapp.libraries.stdlib.run` function cannot be used.
