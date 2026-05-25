from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_metaobjectdump(py_file: Path) -> list[dict]:
    result = subprocess.run(
        ["pyside6-metaobjectdump", str(py_file)],
        check=True,
        capture_output=True,
        text=True,
    )

    if not result.stdout.strip():
        return []

    return json.loads(result.stdout)


def qml_type_for(meta_type: str) -> str:
    return {
        "QString": "QString",
        "bool": "bool",
        "int": "int",
        "double": "double",
        "float": "double",
        "QObject": "QObject",
        "QVariantMap": "QVariantMap",
        "QVariantList": "QVariantList",
    }.get(meta_type, meta_type or "var")


def emit_component(cls: dict, module_name: str) -> list[str]:
    class_name = cls["className"]
    prototype = "QObject"

    super_classes = cls.get("superClasses", [])
    if super_classes:
        prototype = super_classes[0].get("name", "QObject") or "QObject"

    lines = [
        "    Component {",
        f'        name: "{class_name}"',
        '        accessSemantics: "reference"',
        f'        prototype: "{prototype}"',
        f'        exports: ["{module_name}/{class_name} 1.0"]',
    ]

    seen_props: set[str] = set()
    for prop in cls.get("properties", []):
        name = prop.get("name", "")
        prop_type = qml_type_for(prop.get("type", "var"))
        if not name or name in seen_props:
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

        parts = [f'        Method {{ name: "{name}"']
        if return_type and return_type != "void":
            parts.append(f'; type: "{return_type}"')

        for i, arg in enumerate(args):
            arg_name = arg.get("name") or f"arg{i + 1}"
            arg_type = qml_type_for(arg.get("type", "var"))
            parts.append(
                f'; Parameter {{ name: "{arg_name}"; type: "{arg_type}" }}'
            )

        parts.append(" }")
        lines.append("".join(parts))

    lines.append("    }")
    return lines


def generate_qmltypes(base_dir: Path, output_file: Path, module_name: str) -> None:
    py_files = sorted(
        path
        for path in base_dir.rglob("*.py")
        if path.name != "__init__.py"
    )

    lines = ["Module {"]

    seen_classes: set[str] = set()

    for py_file in py_files:
        try:
            dump = run_metaobjectdump(py_file)
        except subprocess.CalledProcessError as exc:
            print(f"[skip] {py_file}: metaobjectdump failed", file=sys.stderr)
            if exc.stderr:
                print(exc.stderr.strip(), file=sys.stderr)
            continue
        except json.JSONDecodeError:
            print(f"[skip] {py_file}: invalid JSON output", file=sys.stderr)
            continue

        for item in dump:
            for cls in item.get("classes", []):
                class_infos = {
                    info.get("name"): info.get("value")
                    for info in cls.get("classInfos", [])
                }

                if "QML.Element" not in class_infos:
                    continue

                class_name = cls.get("className", "")
                if not class_name or class_name in seen_classes:
                    continue

                seen_classes.add(class_name)
                lines.extend(emit_component(cls, module_name))

    lines.append("}")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {output_file}")
    print(f"Components: {len(seen_classes)}")


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