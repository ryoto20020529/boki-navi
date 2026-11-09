#!/usr/bin/env python3
"""src/pages/*.html の <!--@name--> を src/partials/<name>.html で置換し、リポジトリ直下へ出力する。
src/root/ のファイル（sitemap.xml・robots.txt）もリポジトリ直下へ出力する。
どちらも {{SITE}} をサイトのURLに置き換える。

使い方: python3 tools/build.py
独自ドメインへ移行するときは SITE を書き換えて再実行するだけでよい。"""
import argparse, pathlib, re

SITE = "https://boki-navi.vercel.app"  # 末尾スラッシュなし

root = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--out", help="出力先ディレクトリ（省略時はリポジトリ直下。tools/check.py が差分検査に使う）")
out_dir = pathlib.Path(ap.parse_args().out).resolve() if ap.parse_args().out else root
out_dir.mkdir(parents=True, exist_ok=True)
partials = {p.stem: p.read_text(encoding="utf-8").rstrip("\n") for p in (root / "src/partials").glob("*.html")}
alias = {"head": "head-common"}

for page in sorted((root / "src/pages").glob("*.html")):
    html = page.read_text(encoding="utf-8")
    def sub(m):
        key = alias.get(m.group(1), m.group(1))
        if key not in partials:
            raise SystemExit(f"{page.name}: unknown partial {m.group(1)}")
        return partials[key]
    out = re.sub(r"<!--@([\w-]+)-->", sub, html).replace("{{SITE}}", SITE)
    (out_dir / page.name).write_text(out, encoding="utf-8")
    print("built", page.name)

for f in sorted((root / "src/root").iterdir()):
    (out_dir / f.name).write_text(f.read_text(encoding="utf-8").replace("{{SITE}}", SITE), encoding="utf-8")
    print("built", f.name)
