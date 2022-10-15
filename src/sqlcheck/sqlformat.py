import os
import re
import sys
from pathlib import Path
from typing import Union

import sqlparse

PATH_TYPE = Union[str, bytes, os.PathLike]


def usage():
    cmd = Path(__file__).name
    print(f"Usage: {cmd} <file>")
    print(f"       {cmd} <directory>")


def main():

    if len(sys.argv) != 2:
        usage()
        exit()

    target = Path(sys.argv[1]).resolve()

    if target.is_file():
        lines = format_file(target)
        print("".join(lines), end="")
    elif target.is_dir():
        for f in target.glob("*.sql"):
            print(f)
            lines = format_file(f)
            output_file = f
            backup_file = f.with_suffix(".sql.bak")
            f.rename(backup_file)
            with output_file.open("w", encoding="utf-8", newline="\n") as f:
                f.writelines(lines)
    else:
        print(f"Error: No such file or directory: {target}", file=sys.stderr)


def format_file(filepath: PATH_TYPE) -> list[str]:
    with open(filepath, "r", encoding="utf-8") as f:
        lines = format(f.read())
    return lines


def format(source: str) -> list[str]:
    def _format(sql: str) -> list[str]:
        lines = []
        for s in sqlparse.split(sql):
            if lines:
                lines.append("\n")
            s = sqlparse.format(
                s,
                keyword_case="upper",
                identifier_case="upper",
                strip_comments=True,
                reindent=True,
                use_space_around_operators=True,
            )
            s += "\n"
            lines.extend(s.splitlines(keepends=True))
        return lines

    lines = []
    block = ""

    for line in source.splitlines():

        # 空行
        if re.match(r"^\s*$", line):
            if block:
                lines.extend(_format(block))
                block = ""
            if lines and lines[-1] != "\n":
                lines.append("\n")
            continue

        # コメント行
        if re.match(r"^\s*#", line):
            if block:
                lines.extend(_format(block))
                block = ""
            lines.append(line + "\n")
            continue

        block += line + "\n"

    if block:
        lines.extend(_format(block))

    return lines


if __name__ == "__main__":
    main()
