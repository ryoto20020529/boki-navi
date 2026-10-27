#!/usr/bin/env python3
"""src/pages/*.html の <!--@name--> を src/partials/<name>.html で置換し、リポジトリ直下へ出力する。
使い方: python3 tools/build.py   （ヘッダー・フッター・フォームを変更したら必ず再実行）"""
import pathlib, re

root = pathlib.Path(__file__).resolve().parent.parent
partials = {p.stem: p.read_text(encoding="utf-8").rstrip("\n") for p in (root / "src/partials").glob("*.html")}
alias = {"head": "head-common"}

for page in sorted((root / "src/pages").glob("*.html")):
    html = page.read_text(encoding="utf-8")
    def sub(m):
        key = alias.get(m.group(1), m.group(1))
        if key not in partials:
            raise SystemExit(f"{page.name}: unknown partial {m.group(1)}")
        return partials[key]
    out = re.sub(r"<!--@([\w-]+)-->", sub, html)
    (root / page.name).write_text(out, encoding="utf-8")
    print("built", page.name)
