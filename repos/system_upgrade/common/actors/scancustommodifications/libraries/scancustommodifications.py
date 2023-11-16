import ast
import os

from leapp.exceptions import StopActorExecution
from leapp.libraries.common import rpms
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import CustomModifications

LEAPP_REPO_DIRS = ['/usr/share/leapp-repository']
LEAPP_PACKAGES_TO_IGNORE = ['snactor']


def _get_dirs_to_check(component):
    if component == 'repository':
        return LEAPP_REPO_DIRS
    return []


def _get_rpms_to_check(component=None):
    if component == 'repository':
        return rpms.get_leapp_packages(component=rpms.LeappComponents.REPOSITORY)
    if component == 'framework':
        return rpms.get_leapp_packages(component=rpms.LeappComponents.FRAMEWORK)
    return rpms.get_leapp_packages(components=[rpms.LeappComponents.REPOSITORY, rpms.LeappComponents.FRAMEWORK])


def deduce_actor_name(a_file):
    """
    A helper to map an actor/library to the actor name
    If a_file is an actor or an actor library, the name of the actor (name attribute of actor class) will be returned.
    Empty string is returned if the file could not be associated with any actor.
    """
    if not os.path.exists(a_file):
        return ''
    # NOTE(ivasilev) Actors reside only in actor.py files, so AST processing any other file can be skipped.
    # In case this function has been called on a non-actor file, let's go straight to recursive call on the assumed
    # location of the actor file.
    if os.path.basename(a_file) == 'actor.py':
        data = None
        with open(a_file) as f:
            try:
                data = ast.parse(f.read())
            except TypeError:
                api.current_logger().warning('An error occurred while parsing %s, can not deduce actor name', a_file)
                return ''
        # NOTE(ivasilev) Making proper syntax analysis is not the goal here, so let's get away with the bare minimum.
        # An actor file will have an Actor ClassDef with a name attribute and a process function defined
        actor = next((obj for obj in data.body if isinstance(obj, ast.ClassDef) and obj.name and
                      any(isinstance(o, ast.FunctionDef) and o.name == 'process' for o in obj.body)), None)
        # NOTE(ivasilev) obj.name attribute refers only to Class name, so for fetching name attribute need to go
        # deeper
        if actor:
            try:
                actor_name = next((expr.value.s for expr in actor.body
                                   if isinstance(expr, ast.Assign) and expr.targets[-1].id == 'name'), None)
            except (AttributeError, IndexError):
                api.current_logger().warning("Syntax Analysis for %d has failed", a_file)
                actor_name = None
            if actor_name:
                return actor_name

    # Assuming here we are dealing with a library or a file, so let's discover actor filename and deduce actor name
    # from it. Actor is expected to be found under ../../actor.py
    def _check_assumed_location(subdir):
        assumed_actor_file = os.path.join(a_file.split(subdir)[0], 'actor.py')
        if not os.path.exists(assumed_actor_file):
            # Nothing more we can do - no actor name mapping, return ''
            return ''
        return deduce_actor_name(assumed_actor_file)

    return _check_assumed_location('libraries') or _check_assumed_location('files')


def _run_command(cmd, warning_to_log, checked=True):
    """
    A helper that executes a command and returns a result or raises StopActorExecution.
    Upon success results will contain a list with line-by-line output returned by the command.
    """
    try:
        res = run(cmd, checked=checked)
        output = res['stdout'].strip()
        if not output:
            return []
        return output.split('\n')
    except CalledProcessError:
        api.current_logger().warning(warning_to_log)
        raise StopActorExecution()


def _modification_model(filename, change_type, component, rpm_checks_str=''):
    # XXX FIXME(ivasilev) Actively thinking if different model classes inheriting from CustomModifications
    # are needed or let's get away with one model for everything (as is implemented now).
    # The only difference atm is that actor_name makes sense only for repository modifications.
    return CustomModifications(filename=filename, type=change_type, component=component,
                               actor_name=deduce_actor_name(filename), rpm_checks_str=rpm_checks_str)


def check_for_modifications(component):
    """
    This will return a list of any untypical files or changes to shipped leapp files discovered on the system.
    An empty list means that no modifications have been found.
    """
    rpms = _get_rpms_to_check(component)
    dirs = _get_dirs_to_check(component)
    source_of_truth = []
    leapp_files = []
    # Let's collect data about what should have been installed from rpm
    for rpm in rpms:
        res = _run_command(['rpm', '-ql', rpm], 'Could not get a list of installed files from rpm {}'.format(rpm))
        source_of_truth.extend(res)
    # Let's collect data about what's really on the system
    for directory in dirs:
        res = _run_command(['find', directory, '-type', 'f'],
                           'Could not get a list of leapp files from {}'.format(directory))
        leapp_files.extend(res)
    # Let's check for unexpected additions
    custom_files = sorted(set(leapp_files) - set(source_of_truth))
    # Now let's check for modifications
    modified_files = []
    modified_configs = []
    for rpm in rpms:
        res = _run_command(
                ['rpm', '-V', '--nomtime', rpm], 'Could not check authenticity of the files from {}'.format(rpm),
                # NOTE(ivasilev) check is False here as in case of any changes found exit code will be 1
                checked=False)
        if res:
            api.current_logger().warning('Modifications to leapp files detected!\n%s', res)
            for modification_str in res:
                modification = tuple(modification_str.split())
                if len(modification) == 3 and modification[1] == 'c':
                    # Dealing with a configuration that will be displayed as ('S.5......', 'c', '/file/path')
                    modified_configs.append(modification)
                else:
                    # Modification of any other rpm file detected
                    modified_files.append(modification)
    return ([_modification_model(filename=f[1], component=component, rpm_checks_str=f[0], change_type='modified')
             # Let's filter out pyc files not to clutter the output as pyc will be present even in case of
             # a plain open & save-not-changed that we agreed not to react upon.
             for f in modified_files if not f[1].endswith('.pyc')] +
            [_modification_model(filename=f, component=component, change_type='custom')
             for f in custom_files] +
            [_modification_model(filename=f[2], component='configuration', rpm_checks_str=f[0], change_type='modified')
            for f in modified_configs])


def scan():
    return check_for_modifications('framework') + check_for_modifications('repository')
