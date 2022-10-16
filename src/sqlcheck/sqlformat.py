import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Generator, Union

import sqlparse
from sqlparse.sql import Identifier, IdentifierList, Parenthesis, Token
from sqlparse.tokens import Comment, Keyword, Name, Punctuation, String, Whitespace

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


def _is_create_table(sql: str) -> bool:
    return re.match(r"\s*CREATE\s+TABLE", sql.upper()) is not None


def _is_whitespace(token: Token) -> bool:
    if not token:
        return True
    if token.ttype in Whitespace or token.ttype in Comment:
        return True
    return False


def _is_comma(token: Token) -> bool:
    return token.match(Punctuation, ",")


def _is_paren(token: Token) -> bool:
    return token.match(Punctuation, "(") or token.match(Punctuation, ")")


def _is_colname(token: Token) -> bool:
    if isinstance(token, Identifier):
        return True
    if token.ttype in String:
        return True
    return False


def _skip_whitespace(tokens: list[Token]) -> Generator[Token, None, None]:
    for t in tokens:
        if _is_whitespace(t):
            continue
        yield t


def _get_value(token: Token) -> str:
    if isinstance(token, Identifier):
        return token.value.upper()
    if token.ttype in Keyword or token.ttype in Name:
        return token.value.upper()
    return token.value


def _get_width(text: str) -> int:
    count = 0
    for c in text:
        if unicodedata.east_asian_width(c) in "FWA":
            count += 2
        else:
            count += 1
    return count


def _format_sql(sql: str) -> str:
    return sqlparse.format(
        sql,
        keyword_case="upper",
        identifier_case="upper",
        strip_comments=True,
        reindent=True,
        use_space_around_operators=True,
    )


def _format_create_table(query: str) -> str:

    parsed = sqlparse.parse(query)[0]
    formatted = ""

    # 括弧まで
    index = -1
    values = []
    for i, t in enumerate(parsed.tokens):
        if isinstance(t, Parenthesis):
            index = i
            break
        if _is_whitespace(t):
            continue
        values.append(_get_value(t))
    values.append("(\n")
    formatted += " ".join(values)

    # 括弧の中身をカラムに分割する
    tokens = []
    columns = []
    colname_width = 0
    paren = parsed.tokens[index]
    for t in _skip_whitespace(paren[1:-1]):  # 一番外側の括弧は除く
        # カンマまでがひとつのカラム定義
        if _is_comma(t):
            tokens.append(t)
            columns.append(tokens)
            tokens = []
        # 識別子が続くと IdentifierList にまとめられる
        # 制約 → カンマ + 改行 → フィールド名となっていてもまとめられてしまう
        elif isinstance(t, IdentifierList):
            for u in _skip_whitespace(t.tokens):
                if _is_comma(u):
                    tokens.append(u)
                    columns.append(tokens)
                    tokens = []
                else:
                    tokens.extend(_skip_whitespace(list(u.flatten())))
                    if _is_colname(u):
                        colname_width = max(colname_width, _get_width(u.value))
        else:
            tokens.extend(_skip_whitespace(list(t.flatten())))
            if _is_colname(t):
                colname_width = max(colname_width, _get_width(t.value))
    if tokens:
        columns.append(tokens)

    # カラムごとに整形する
    for col in columns:
        # インデント
        formatted += "    "
        # カラム名は幅を合わせる
        t = col[0]
        if t.ttype in Name or t.ttype in String:
            width = len(t.value) + colname_width - _get_width(t.value)
            formatted += f"{_get_value(t):<{width}}"
        else:
            # PRIMARY KEY (field, ...) の場合は空白で埋めない
            formatted += _get_value(t)
        # カラム名以降の制約など
        prev = ""
        for t in col[1:]:
            if _is_comma(t) or _is_paren(t):
                formatted += _get_value(t)
            else:
                if prev == "(":
                    formatted += _get_value(t)
                else:
                    formatted += " " + _get_value(t)
            prev = t.value
        formatted += "\n"

    # カラム定義の終わり
    formatted += ")"

    # 括弧から後
    # セミコロンまでを整形して出力
    index += 1
    values = []
    for t in _skip_whitespace(parsed.tokens[index:]):
        if t.match(Punctuation, ";"):
            if values:
                formatted += "\n" + _format_sql(" ".join(values))
            formatted += ";\n"
            break
        values.append(_get_value(t))

    return formatted


def _format_query(query: str) -> list[str]:

    lines = []

    for sql in sqlparse.split(query):
        if lines:
            lines.append("\n")
        if _is_create_table(sql):
            sql = _format_create_table(sql)
        else:
            sql = _format_sql(sql) + "\n"
        lines.extend(sql.splitlines(keepends=True))

    return lines


def format_query(query: str) -> list[str]:

    lines = []
    block = ""

    for line in query.splitlines():

        # 空行
        if re.match(r"^\s*$", line):
            if block:
                lines.extend(_format_query(block))
                block = ""
            if lines and not re.match(r"^\s*\n\s*$", lines[-1]):
                lines.append("\n")
            continue

        # コメント行
        if re.match(r"^\s*#", line):
            if block:
                lines.extend(_format_query(block))
                block = ""
            lines.append(line + "\n")
            continue

        block += line + "\n"

    if block:
        lines.extend(_format_query(block))

    return lines


def format_file(filepath: PATH_TYPE) -> list[str]:
    with open(filepath, "r", encoding="utf-8") as f:
        lines = format_query(f.read())
    return lines


if __name__ == "__main__":
    main()
