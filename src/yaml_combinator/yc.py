#!/usr/bin/env python3
"""
yc.py

Reads one or more YAML files, resolves '#!import "filepath"' directives by
inlining the referenced file's content, then resolves YAML anchor-style
variable definitions (&VAR_NAME value) by substituting all *VAR_NAME
references with the captured value.  The final combinated text is written to
stdout or a specified output file/device.

The files are validated as well-formed YAML before processing, but all
substitution work is done on the raw text (not the parsed tree).
"""

import argparse
import re
import sys
from pathlib import Path

import yaml  # PyYAML — install with: pip install pyyaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def validate_yaml(text: str, source: str) -> None:
    """Raise SystemExit if *text* is not valid YAML."""
    try:
        yaml.safe_load(text)
    except yaml.YAMLError as exc:
        sys.exit(f"ERROR: {source} is not valid YAML:\n{exc}")


_IMPORT_RE = re.compile(r"""^[ \t]*#!import\s+"([^"]+)"\s*$""", re.MULTILINE)


def resolve_imports(text: str, base_dir: Path, visited: set[str]) -> str:
    """
    Recursively replace every '#!import "filepath"' line with the raw
    contents of that file (relative to *base_dir*).

    Circular imports are detected and cause a hard exit.
    """
    def _replace(match: re.Match) -> str:
        path = match.group(1)
        if not (full_path:=Path(path)).is_absolute():
            full_path = (base_dir / path).resolve()
        key = str(full_path)

        if key in visited:
            sys.exit(f"ERROR: Circular import detected for '{full_path}'")

        if not full_path.exists():
            sys.exit(f"ERROR: Imported file not found: '{full_path}'")

        imported_text = full_path.read_text(encoding="utf-8")
        validate_yaml(imported_text, str(full_path))

        # Recurse so that imported files can themselves have imports,
        # resolving relative to the imported file's own directory.
        imported_text = resolve_imports(
            imported_text,
            base_dir,
            visited | {key},
        )
        # Strip a trailing newline from the imported block so we don't
        # accumulate blank lines; the surrounding text already has one.
        return imported_text.rstrip("\n")

    return _IMPORT_RE.sub(_replace, text)


# Match the *definition* side: &VAR_NAME followed by the scalar value on the
# same line, e.g.:
#   platform: &PLATFORM bun
#   version: &VERSION "1.0.0"
#
# Group 1 = VAR_NAME, Group 2 = raw value token (possibly quoted)
_ANCHOR_DEF_RE = re.compile(
    r"""&([A-Za-z_][A-Za-z0-9_]*)          # &VAR_NAME
        [ \t]+                               # mandatory whitespace
        ("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|[^\s,\[\]{}"'#][^\s,\[\]{}]*)
                                             # scalar value (quoted or bare)
    """,
    re.VERBOSE,
)

# Match the *reference* side: *VAR_NAME (not immediately preceded by & so we
# don't clobber definitions)
_ANCHOR_REF_RE = re.compile(r"(?<!&)\*([A-Za-z_][A-Za-z0-9_]*)")


def resolve_anchors(text: str) -> str:
    """
    1. Scan all &VAR_NAME <value> definitions and build a substitution map.
    2. Replace every *VAR_NAME reference with its captured value.

    Definition lines are left intact (the &VAR_NAME tag stays); only the
    *VAR_NAME alias occurrences are replaced.
    """
    anchor_map: dict[str, str] = {}

    for m in _ANCHOR_DEF_RE.finditer(text):
        name, value = m.group(1), m.group(2)
        anchor_map[name] = value  # last definition wins (like real YAML)

    if not anchor_map:
        return text

    def _replace_ref(match: re.Match) -> str:
        name = match.group(1)
        return anchor_map.get(name, match.group(0))  # unknown ref → leave as-is

    return _ANCHOR_REF_RE.sub(_replace_ref, text)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_combinated(input_files: list[Path], base_dir: Path) -> str:
    """Read, validate, resolve imports, then concatenate all input files."""
    parts: list[str] = []

    for path in input_files:
        if not path.exists():
            sys.exit(f"ERROR: Input file not found: '{path}'")

        raw = path.read_text(encoding="utf-8")
        validate_yaml(raw, str(path))

        resolved = resolve_imports(raw, base_dir, visited={str(path.resolve())})
        parts.append(resolved)

    # Join with a single blank line between files
    return "\n\n".join(part.rstrip("\n") for part in parts) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Combine one or more YAML files: resolve #!import directives and "
            "substitute *VAR_NAME anchor references with their defined values."
        )
    )
    parser.add_argument(
        "inputs",
        metavar="FILE",
        nargs="+",
        type=Path,
        help="One or more input YAML files to process.",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="OUTPUT",
        default="-",
        help=(
            "Output file or device.  Defaults to stdout ('-').  "
            "Use e.g. '/dev/stdout', a filename, or any writable path."
        ),
    )
    args = parser.parse_args()

    combinated = build_combinated(args.inputs, base_dir=Path.cwd())
    combinated = resolve_anchors(combinated)

    if args.output in ("-", "/dev/stdout"):
        sys.stdout.write(combinated)
    else:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(combinated, encoding="utf-8")
        print(f"Written to '{out_path}'", file=sys.stderr)


if __name__ == "__main__":
    main()
