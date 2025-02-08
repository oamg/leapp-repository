# Execute custom script during the upgrade

For some people it could be tricky to write a code in Python and in some cases
they prefer to perform e.g. their shell script during the upgrade. And in some
cases you the code in bash could be just much more simple, when using tools
available on the system. Well, you will always need to do some Python code,
but in case you do not need anything else, just execute the code in the right
phase of the upgrade, here is the minimal actor to do so.

For more tips, check our actors how they work with the `run` function. There
are many useful examples:
 [system\_upgrade\_common repo](https://github.com/oamg/leapp-repository/tree/main/repos/system\_upgrade/common/actors)

The full list of existing phases in the `IPUWorkflow` and their tags see [IPUWorkflow](https://github.com/oamg/leapp-repository/blob/main/repos/system_upgrade/common/workflows/inplace_upgrade.py)

[//]: # (TODO: replace the URL by the link to upstream documentation.)

```python
from leapp.actors import Actor
from leapp.libraries.stdlib import api, CalledProcessError, run

# AI: replace <Phase>PhaseTag by a valid phase tag.
from leapp.tags import <Phase>PhaseTag, IPUWorkflowTag

# AI: change the name of the class when applied!!
class ExecuteMyCustomScript(Actor):
    """
    This actor executes a script (or whatever executable command).

    The actor is executed during the execution of the specified phase.
    You can specify your script as path to the executable file, just
    the name of the executable file if covered by PATH. If it's a custom script,
    we suggest to store it under this actor directory in path:
        tools/<myscript>
    so the directory with actor contains at least:
        actor.py
        tools/<myscript>
    ensure the file has set executable permission! In such a case, during
    the actor execution you can call just <myscript> to execute it
    """

    # AI: change the name when applied!!
    name = 'execute\_my\_custom\_script'
    consumes = ()
    produces = ()
    tags = (IPUWorkflowTag, <Phase>PhaseTag)

    def process(self):
        # Specify the command that should be executed.
        # Pipelines are not allowed. It should be simple command. Each option
        # need to be a different item in the array. The first item is the
        # executable. Example:
        # command = ['/usr/bin/echo', '-E', 'I have been executed...']
        command = ['<myscript>']
        try:
            #
            run(command)
        except CalledProcessError as e:
            # This happens if the command ends with non-zero exit code
            self.current_logger().error('<Your error msg>')
            details = {
                'details': str(err),
                'stderr': err.stderr,
                'stdout': err.stdout
            }
            # Here you can decide what to do next. E.g. If you want to end with
            # error and stop the upgrade process, uncomment the raise of exception
            # below.
            # # Note that usually you do not want to raise this error after the
            # # upgrade DNF transaction has been performed as the system usually
            # # ends just in emergency mode and more broken state.
            # # In short, it is safe in phases prior the first reboot.
            # raise StopActorExecutionError('Your error msg', details=details)

        except OSError as e:
            # This can happen just if the command is not possible to execute.
            # E.g. the executable does not exist, it has not set executable
            # mode, etc.
            self.current_logger().error(
                'Cannot execute cmd "{}": {}'
                .format(command, str(e))
            )
            # Similarly, in case you want to stop the upgrade execution with error:
            #
            # raise StopActorExecutionError('Your err msg')
```
