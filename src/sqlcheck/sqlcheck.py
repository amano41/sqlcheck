import os
import re
import sys
from pathlib import Path
from typing import Union

from mindiff import mindiff

from .sqlformat import format_query

PATH_TYPE = Union[str, bytes, os.PathLike]


def usage():
    cmd = Path(__file__).name
    print(f"Usage: {cmd} <file> <answer>")
    print(f"       {cmd} <directory> <answer>")


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
            answer_sql = f.read()

        for target_file in target_path.glob("*.sql"):

            print(target_file)
            with target_file.open(encoding="utf-8") as f:
                target_sql = f.read()

            lines = check(target_sql, answer_sql)

            output_file = target_file.with_suffix(".diff")
            with output_file.open("w", encoding="utf-8", newline="\n") as f:
                f.writelines(lines)

    # 読み込めない場合はエラー
    else:
        print(f"Error: No such file or directory: {target_path}", file=sys.stderr)


def check_file(target_file: PATH_TYPE, answer_file: PATH_TYPE) -> list[str]:
    # フォーマット等の前処理を適用するため check() に行データを渡す
    # mindiff にはファイルを比較する compare_file() もあるが使わない
    with open(target_file, "r", encoding="utf-8") as f:
        target_sql = f.read()
    with open(answer_file, "r", encoding="utf-8") as f:
        answer_sql = f.read()
    return check(target_sql, answer_sql)


def check(target_sql: str, answer_sql: str) -> list[str]:

    # ダブルクォーテーションはデータベースによって扱いが異なるので削除しておく
    # 多くの RDBMS では識別子に予約語や特殊文字を使用したい場合のエスケープ用だが，
    # MySQL では文字列として，SQLite でも文脈によって文字列として解釈される
    target_sql = target_sql.replace('"', "")
    answer_sql = answer_sql.replace('"', "")

    # 整形して行単位に分割
    target_lines = format_query(target_sql)
    answer_lines = format_query(answer_sql)

    # mindiff は file2 のどの行が file1 から変わっているかを出力する
    # target のどこに間違いがあるかを示すためには引数を A → T の順にすればよい
    # 引数の順番を入れ替えると追加・削除のマーカーも逆になるので元に戻す必要がある
    table = {"+": "-", "-": "+"}
    lines = []
    for line in mindiff.compare(answer_lines, target_lines):
        line = re.sub(r"^[+-]", lambda m: table[m.group(0)], line)
        lines.append(line)

    return lines


if __name__ == "__main__":
    main()
