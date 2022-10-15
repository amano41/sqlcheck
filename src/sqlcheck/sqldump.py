import os
import sqlite3
import sys
from pathlib import Path
from typing import Union

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
        lines = dump(target)
        print("".join(lines), end="")
    elif target.is_dir():
        for f in target.glob("*.db"):
            print(f)
            lines = dump(f)
            output_file = f.with_suffix(".sql")
            with open(output_file, "w", encoding="utf-8", newline="\n") as f:
                f.writelines(lines)
    else:
        print(f"Error: No such file or directory: {target}", file=sys.stderr)


def dump(filepath: PATH_TYPE) -> list[str]:

    lines = []

    con = sqlite3.connect(filepath)
    for block in con.iterdump():
        if "sqlite_sequence" in block:
            continue
        for line in block.splitlines():
            lines.append(line + "\n")
    con.close()

    return lines


if __name__ == "__main__":
    main()
