"""
Stubfile generator for leapp model classes.

This generator overcomes the limitations of mypy.stubgen for generation of type
stubs for models in the leapp framework:
- Types in leapp.fields are mapped to Python types, e.g. field.String() -> str
- Docstrings for fields are preserved
- Fake __init__ function are generated with typed/named arguments

Can also be imported and used as a module

Note: This script doesn't handle imports, it's designed to be used in
conjunction with the utils/gen_stubs.sh script which handles imports.

Note: The script heavily relies on the basic structure of model classes and
does very minimal checks for conformity.
"""

import argparse
import ast
import sys
from pathlib import Path

# Mapping of leapp field types to Python types
BASIC_TYPE_MAP = {
    "String": "str",
    "Integer": "int",
    "Boolean": "bool",
    "Float": "float",
    "Blob": "bytes",
    "DateTime": "datetime.datetime",
    # TODO JSON is unhandled as it's currently unused
}


def _resolve_leapp_enum(node: ast.Call) -> str:
    """
    :param node: The RHS of the field assignment
    """
    if node.args and isinstance(node.args[0], ast.List):
        # extract values: ['disable', 'enable'] -> "'disable', 'enable'"
        values = []
        for elem in node.args[0].elts:
            if isinstance(elem, ast.Constant):
                # use repr() to keep quotes around strings
                values.append(repr(elem.value))
        return f"Literal[{', '.join(values)}]"
    return "Incomplete"


def resolve_leapp_wrapper_type(node: ast.expr) -> str:
    """Recursively resolves fields.Type() to a PEP 484 type string."""

    # Check if it's a function call like fields.String() or fields.List(...)
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.value.id == "fields":
            field_type = func.attr

            if field_type == "Nullable":
                inner = resolve_leapp_wrapper_type(node.args[0])
                return f"{inner} | None"

            if field_type == "List":
                inner = resolve_leapp_wrapper_type(node.args[0])
                return f"list[{inner}]"

            if field_type == "Model":
                inner = resolve_leapp_wrapper_type(node.args[0])
                return f"{inner}"

            if field_type in ("StringEnum", "IntegerEnum", "FloatEnum", "NumberEnum"):
                return _resolve_leapp_enum(node)

            if field_type == "StringMap":
                value_type = resolve_leapp_wrapper_type(node.args[0])
                return f"dict[str, {value_type}]"

            basic_type = BASIC_TYPE_MAP.get(field_type)
            if not basic_type:
                sys.stderr.write(f"Warning: Unhandled field type: {field_type}")
                return "Incomplete"

            return basic_type

    # Fallback for simple assignments (like topic = SystemFactsTopic)
    elif isinstance(node, ast.Name):
        return node.id

    return "Any"


def process_model_body(body: list[ast.stmt]):
    init_args = []

    for i, item in enumerate(body):
        if not isinstance(item, ast.Assign):
            continue

        assert len(item.targets) == 1, "Multiple assignments are unexpected in a Model"
        target = item.targets[0]

        if not isinstance(target, ast.Name):
            continue

        field_name = target.id
        field_type = resolve_leapp_wrapper_type(item.value)
        yield f"    {field_name}: {field_type}"

        if field_name != "topic":
            init_args.append((field_name, field_type))

        # Look ahead for field docstrings
        if i + 1 < len(body):
            next_node = body[i + 1]
            if isinstance(next_node, ast.Expr) and isinstance(
                next_node.value, ast.Constant
            ):
                if isinstance(next_node.value.value, str):
                    field_doc = next_node.value.value
                    yield f'    """{field_doc}"""'

    # add a fake __init__, leapp has a generic init in the Model class, so to
    # have signature info with types and possible fields we add the specific
    # fake on Model subclasses
    if init_args:
        # add the = ... to instruct the type checkers that a default value
        # exists, but is not important for type inference/checking
        args = [f"{fname}: {ftype} = ..." for (fname, ftype) in init_args]
        args_str = ", ".join(args)
        yield f"    def __init__(self, {args_str}) -> None: ..."


def generate_stubs_from_source(source_code: str) -> str:
    tree = ast.parse(source_code)
    output = []

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue

        # Extract the base class (e.g., Model)
        # NOTE: No checking is done if the base class is (a subclass of) the
        # Model class, such classes should never appear in model files.
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]

        base_str = f"({', '.join(bases)})" if bases else ""
        output.append(f"class {node.name}{base_str}:")

        doc = ast.get_docstring(node, clean=False)
        if doc:
            output.append(f'    """{doc}"""')

        body = list(process_model_body(node.body)) or ["    ..."]
        output += body
        output.append("")

    return "\n".join(output)


def main(infile: Path, outdir: Path):
    outfile = outdir / (infile.name + "i")

    stub_str = generate_stubs_from_source(infile.read_text())
    outfile.write_text(stub_str)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.stderr.write("Usage: gen_model_stubs <input_file.py> <output_dir>")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Source file with model definition(s)",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output file")

    args = parser.parse_args()
    main(args.source, args.output)
