import os
import re
import sys
from difflib import Differ
from pathlib import Path
from typing import Union

PATH_TYPE = Union[str, bytes, os.PathLike]


def usage():
    cmd = Path(__file__).name
    print(f"Usage: python {cmd} <file> <answer>")
    print(f"       python {cmd} <directory> <answer>")


def main():

    if len(sys.argv) != 3:
        usage()
        exit()

    target_path = Path(sys.argv[1])
    answer_path = Path(sys.argv[2])

    # 採点対象がファイルの場合
    if target_path.is_file():
        lines = check_file(target_path, answer_path)
        print("".join(lines), end="")

    # 採点対象がディレクトリの場合
    elif target_path.is_dir():

        with answer_path.open(encoding="utf-8") as f:
            answer_sql = f.readlines()

        for target_file in target_path.glob("*.sql"):

            print(target_file)
            with target_file.open(encoding="utf-8") as f:
                target_sql = f.readlines()

            lines = check(target_sql, answer_sql)

            output_file = target_file.with_suffix(".diff")
            with output_file.open("w", encoding="utf-8", newline="\n") as f:
                f.writelines(lines)

    # 読み込めない場合はエラー
    else:
        print(f"Error: No such file or directory: {target_path}", file=sys.stderr)


def check_file(target_file: PATH_TYPE, answer_file: PATH_TYPE) -> list[str]:

    with open(target_file, "r", encoding="utf-8") as f:
        target_sql = f.readlines()

    with open(answer_file, "r", encoding="utf-8") as f:
        answer_sql = f.readlines()

    return check(target_sql, answer_sql)


def check(target: list[str], answer: list[str]) -> list[str]:

    result = []

    # ダブルクォーテーションを削除
    target = [t.replace('"', "") for t in target]
    answer = [a.replace('"', "") for a in answer]

    differ = Differ()
    lines = list(differ.compare(target, answer))

    n = len(lines)
    i = 0

    while i < n:

        line = lines[i]
        i = i + 1

        # 差異のある場所を示すマーカー行は出力しない
        if line.startswith("? "):
            continue

        # target 側にのみ存在する行
        if line.startswith("- "):
            # 次の行がマーカー行であれば差異のある行
            # 必ず answer 側の + 行と ? 行が続くのでスキップする
            # 削除するべき行ではなく修正するべき行なのでマーカーを * に変更する
            if i < n:
                next_line = lines[i]
                if next_line.startswith("? "):
                    i = i + 2
                    line = re.sub(r"^-", "*", line)
            result.append(line)
            continue

        # answer 側にのみ存在する行
        if line.startswith("+ "):
            # 次の行がマーカー行であれば差異のある行
            # target 側で出力済みなので出力しなくてよい
            # 次の行がマーカー行でなかった場合は追加するべき行なので出力する
            if i < n:
                next_line = lines[i]
                if next_line.startswith("? "):
                    continue
            result.append(line)
            continue

        # 同一の行はそのまま出力
        result.append(line)

    return result


if __name__ == "__main__":
    main()
