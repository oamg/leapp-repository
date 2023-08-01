import argparse
import ast
import os
import sys


def is_direct_actor_def(ast_node):
    if not isinstance(ast_node, ast.ClassDef):
        return False

    direcly_named_bases = (base for base in ast_node.bases if isinstance(base, ast.Name))
    for class_base in direcly_named_bases:
        # We are looking for direct name 'Actor'
        if class_base.id == 'Actor':
            return True

    return False


def extract_actor_name_from_def(actor_class_def):
    assignment_value_class = ast.Str if sys.version_info < (3,8) else ast.Constant
    assignment_value_attrib = 's' if sys.version_info < (3,8) else 'value'

    actor_name = None
    class_level_assignments = (child for child in actor_class_def.body if isinstance(child, ast.Assign))
    # Search for class-level assignment specifying actor's name: `name = 'name'`
    for child in class_level_assignments:
        assignment = child
        for target in assignment.targets:
            assignment_adds_name_attrib = isinstance(target, ast.Name) and target.id == 'name'
            assignment_uses_a_constant_string = isinstance(assignment.value, assignment_value_class)
            if assignment_adds_name_attrib and assignment_uses_a_constant_string:
                rhs = assignment.value  # <lhs> = <rhs>
                actor_name = getattr(rhs, assignment_value_attrib)
                break
        if actor_name is not None:
            break
    return actor_name


def get_actor_names(actor_path):
    with open(actor_path) as actor_file:
        try:
            actor_def = ast.parse(actor_file.read())
        except SyntaxError:
            error = ('Failed to parse {0}. The actor might contain syntax errors, or perhaps it '
                     'is written with Python3-specific syntax?\n')
            sys.stderr.write(error.format(actor_path))
            return []
        actor_defs = [ast_node for ast_node in actor_def.body if is_direct_actor_def(ast_node)]
        actors = [extract_actor_name_from_def(actor_def) for actor_def in actor_defs]
    return actors


def make_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('actor_names', nargs='+',
                        help='Actor names (the name attribute of the actor class) to look for.')
    parser.add_argument('-C', '--change-dir', dest='cwd',
                        help='Path in which the actors will be looked for.', default='.')
    return parser


if __name__ == '__main__':
    parser = make_parser()
    args = parser.parse_args()
    cwd = os.path.abspath(args.cwd)
    actor_names_to_search_for = set(args.actor_names)

    actor_paths = []
    for directory, dummy_subdirs, dir_files in os.walk(cwd):
        for actor_path in dir_files:
            actor_path = os.path.join(directory, actor_path)
            if os.path.basename(actor_path) != 'actor.py':
                continue

            defined_actor_names = set(get_actor_names(actor_path))
            if defined_actor_names.intersection(actor_names_to_search_for):
                actor_module_path = directory
                actor_paths.append(actor_module_path)
    print('\n'.join(actor_paths))
