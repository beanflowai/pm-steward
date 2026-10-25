#!/usr/bin/env python3
"""Render {{NAME}} placeholders from the environment. Fails closed."""

import argparse
import os
import re
import sys

PLACEHOLDER = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--allow-empty",
        default="",
        help="comma-separated names that may render empty",
    )
    args = parser.parse_args()

    allowed_empty = {name.strip() for name in args.allow_empty.split(",") if name.strip()}

    try:
        with open(args.template, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        print(f"ERROR: cannot read template: {exc}", file=sys.stderr)
        return 2

    names = sorted(set(PLACEHOLDER.findall(text)))
    missing = [name for name in names if not os.environ.get(name) and name not in allowed_empty]
    if missing:
        print("ERROR: missing values: " + ", ".join(missing), file=sys.stderr)
        return 2

    for name in names:
        text = text.replace("{{" + name + "}}", os.environ.get(name, ""))

    leftover = sorted(set(PLACEHOLDER.findall(text)))
    if leftover:
        print("ERROR: unresolved placeholders: " + ", ".join(leftover), file=sys.stderr)
        return 2

    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.chmod(args.output, 0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
