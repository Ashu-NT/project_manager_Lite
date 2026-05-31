from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path


QMLTYPES_IMPORT = "import QtQuick.tooling 1.2"


def run_metaobjectdump(py_file: Path) -> list[dict]:
    result = subprocess.run(
        ["pyside6-metaobjectdump", str(py_file)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else []


def qml_type_for(meta_type: str) -> str:
    return {
        "QString": "QString",
        "str": "QString",
        "bool": "bool",
        "int": "int",
        "double": "double",
        "float": "double",
        "QObject": "QObject",
        "QVariant": "var",
        "QVariantMap": "QVariantMap",
        "QVariantList": "QVariantList",
        "list": "QVariantList",
        "dict": "QVariantMap",
        "None": "void",
    }.get(meta_type, meta_type or "var")


def collect_python_metadata(py_file: Path) -> dict[str, dict]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    result: dict[str, dict] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        class_data = {
            "methods": {},
            "properties": {},
        }

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                args = [arg.arg for arg in item.args.args]
                if args and args[0] in {"self", "cls"}:
                    args = args[1:]

                class_data["methods"][item.name] = args

                for deco in item.decorator_list:
                    if not isinstance(deco, ast.Call):
                        continue

                    func_name = ""
                    if isinstance(deco.func, ast.Name):
                        func_name = deco.func.id
                    elif isinstance(deco.func, ast.Attribute):
                        func_name = deco.func.attr

                    if func_name != "Property":
                        continue

                    if not deco.args:
                        continue

                    prop_type = None
                    first_arg = deco.args[0]

                    if isinstance(first_arg, ast.Name):
                        prop_type = first_arg.id
                    elif isinstance(first_arg, ast.Constant):
                        prop_type = str(first_arg.value)

                    if prop_type:
                        class_data["properties"][item.name] = qml_type_for(prop_type)

        result[node.name] = class_data

    return result


def class_infos_for(cls: dict) -> dict[str, str]:
    return {
        info.get("name"): info.get("value")
        for info in cls.get("classInfos", [])
    }


def is_qml_element(cls: dict) -> bool:
    infos = class_infos_for(cls)
    return "QML.Element" in infos


def super_class_name(cls: dict) -> str:
    supers = cls.get("superClasses", [])
    if not supers:
        return "QObject"
    return supers[0].get("name", "QObject") or "QObject"


def emit_component(
    cls: dict,
    module_name: str,
    python_meta: dict[str, dict],
    exported: bool,
) -> list[str]:
    class_name = cls["className"]
    prototype = super_class_name(cls)

    lines = [
        "    Component {",
        f'        name: "{class_name}"',
        '        accessSemantics: "reference"',
        f'        prototype: "{prototype}"',
    ]

    if exported:
        lines.append(f'        exports: ["{module_name}/{class_name} 1.0"]')

    py_class_meta = python_meta.get(class_name, {})
    py_methods = py_class_meta.get("methods", {})
    py_properties = py_class_meta.get("properties", {})

    seen_props: set[str] = set()

    for prop in cls.get("properties", []):
        name = prop.get("name", "")
        if not name or name in seen_props:
            continue

        seen_props.add(name)
        prop_type = qml_type_for(prop.get("type", "var"))

        lines.append(
            f'        Property {{ name: "{name}"; type: "{prop_type}"; isReadonly: true }}'
        )

    # Patch custom QObject properties missed or weakened by metaobjectdump.
    for name, prop_type in py_properties.items():
        if name in seen_props:
            continue

        seen_props.add(name)
        lines.append(
            f'        Property {{ name: "{name}"; type: "{prop_type}"; isReadonly: true }}'
        )

    seen_methods: set[str] = set()

    for slot in cls.get("slots", []):
        name = slot.get("name", "")
        if not name or name in seen_methods:
            continue

        seen_methods.add(name)

        return_type = qml_type_for(slot.get("returnType", "void"))
        args = slot.get("arguments", [])
        real_arg_names = py_methods.get(name, [])

        lines.append("        Method {")
        lines.append(f'            name: "{name}"')

        if return_type and return_type != "void":
            lines.append(f'            type: "{return_type}"')

        for i, arg in enumerate(args):
            fallback_name = arg.get("name") or f"arg{i + 1}"
            arg_name = real_arg_names[i] if i < len(real_arg_names) else fallback_name
            arg_type = qml_type_for(arg.get("type", "var"))

            lines.append(
                f'            Parameter {{ name: "{arg_name}"; type: "{arg_type}" }}'
            )

        lines.append("        }")

    lines.append("    }")
    lines.append("")
    return lines


def generate_qmltypes(base_dir: Path, output_file: Path, module_name: str) -> None:
    py_files = sorted(
        path for path in base_dir.rglob("*.py")
        if path.name != "__init__.py"
    )

    all_classes: dict[str, tuple[dict, dict[str, dict]]] = {}
    exported_classes: set[str] = set()
    required_prototypes: set[str] = set()

    for py_file in py_files:
        try:
            python_meta = collect_python_metadata(py_file)
            dump = run_metaobjectdump(py_file)
        except subprocess.CalledProcessError as exc:
            print(f"[skip] {py_file}: metaobjectdump failed", file=sys.stderr)
            if exc.stderr:
                print(exc.stderr.strip(), file=sys.stderr)
            continue
        except json.JSONDecodeError:
            print(f"[skip] {py_file}: invalid JSON output", file=sys.stderr)
            continue
        except SyntaxError as exc:
            print(f"[skip] {py_file}: syntax error: {exc}", file=sys.stderr)
            continue

        for item in dump:
            for cls in item.get("classes", []):
                class_name = cls.get("className", "")
                if not class_name:
                    continue

                all_classes[class_name] = (cls, python_meta)

                if is_qml_element(cls):
                    exported_classes.add(class_name)
                    proto = super_class_name(cls)
                    if proto and proto != "QObject":
                        required_prototypes.add(proto)

    lines = [
        QMLTYPES_IMPORT,
        "",
        "Module {",
    ]

    emitted: set[str] = set()

    # Emit exported QML-facing classes.
    for class_name in sorted(exported_classes):
        cls, python_meta = all_classes[class_name]
        lines.extend(
            emit_component(
                cls=cls,
                module_name=module_name,
                python_meta=python_meta,
                exported=True,
            )
        )
        emitted.add(class_name)

    # Emit non-exported base/prototype classes.
    for class_name in sorted(required_prototypes):
        if class_name in emitted:
            continue

        found = all_classes.get(class_name)
        if not found:
            continue

        cls, python_meta = found
        lines.extend(
            emit_component(
                cls=cls,
                module_name=module_name,
                python_meta=python_meta,
                exported=False,
            )
        )
        emitted.add(class_name)

    lines.append("}")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {output_file}")
    print(f"Exported components: {len(exported_classes)}")
    print(f"Prototype components: {len(emitted - exported_classes)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_dir", help="Base folder to scan recursively")
    parser.add_argument(
        "-o",
        "--output",
        default="ProjectManagement.Controllers.qmltypes",
        help="Output .qmltypes file",
    )
    parser.add_argument(
        "-m",
        "--module",
        default="ProjectManagement.Controllers",
        help="QML module name",
    )

    args = parser.parse_args()

    generate_qmltypes(
        base_dir=Path(args.base_dir).resolve(),
        output_file=Path(args.output).resolve(),
        module_name=args.module,
    )


if __name__ == "__main__":
    main()