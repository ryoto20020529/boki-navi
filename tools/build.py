#!/usr/bin/env python3
"""src/pages/*.html の <!--@name--> を src/partials/<name>.html で置換し、リポジトリ直下へ出力する。
src/root/ のファイル（sitemap.xml・robots.txt）もリポジトリ直下へ出力する。
どちらも {{SITE}} をサイトのURLに置き換える。
src/articles/*.html（コラム記事）からは column/<slug>.html と column/index.html を生成し、sitemap.xml にも追加する。

使い方: python3 tools/build.py
独自ドメインへ移行するときは SITE を書き換えて再実行するだけでよい。"""
import argparse, html as htmllib, json, pathlib, re

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

# ---------- コラム記事 ----------
# src/articles/<slug>.html の先頭に <!--key: value--> 形式で title / description / date / lead / cta（相談フォームの service 値）/ cta_label を書く。
# 本文は .prose の中に入る HTML（h2・h3・p・ul・ol.curri・table.journal など）。H1 は書かない（title から生成する）。
def expand(text):
    def sub(m):
        key = alias.get(m.group(1), m.group(1))
        if key not in partials:
            raise SystemExit(f"unknown partial {m.group(1)}")
        return partials[key]
    return re.sub(r"<!--@([\w-]+)-->", sub, text).replace("{{SITE}}", SITE)

articles = []
for src in sorted((root / "src/articles").glob("*.html")):
    raw = src.read_text(encoding="utf-8")
    meta = dict(re.findall(r"<!--(\w+):\s*(.*?)\s*-->", raw))
    for k in ("title", "description", "date", "lead", "cta", "cta_label"):
        if k not in meta:
            raise SystemExit(f"{src.name}: <!--{k}: ...--> がありません")
    meta["slug"] = src.stem
    meta["body"] = re.sub(r"<!--\w+:.*?-->\n?", "", raw).strip()
    articles.append(meta)
articles.sort(key=lambda m: (m["date"], m["slug"]), reverse=True)
esc = lambda t: htmllib.escape(t, quote=True)

ARTICLE = """<!DOCTYPE html>
<html lang="ja">
<head>
<!--@head-->
  <title>{title}｜簿記合格ナビ</title>
  <meta name="description" content="{description}" />
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large" />
  <link rel="canonical" href="{{{{SITE}}}}/column/{slug}" />
  <meta property="og:url" content="{{{{SITE}}}}/column/{slug}" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{description}" />
  <meta name="twitter:title" content="{title}" />
  <meta name="twitter:description" content="{description}" />
  <script type="application/ld+json">
{jsonld}
  </script>
</head>
<body>
<!--@header-->
<main id="main">
  <nav class="breadcrumb container" aria-label="パンくずリスト"><ol><li><a href="/">ホーム</a></li><li><a href="/column">コラム</a></li><li aria-current="page">{title}</li></ol></nav>
  <article class="article">
    <div class="container prose">
      <p class="article-meta">コラム・<time datetime="{date}">{date_ja}</time> 公開・簿記合格ナビ 運営者 有村稜斗</p>
      <h1>{title}</h1>
      <p class="article-lead">{lead}</p>
{body}
      <aside class="cta-box">
        <p class="cta-box-title">一人で止まっているなら、その論点だけ相談できます</p>
        <p>早稲田大学大学院会計研究科の現役院生が、マンツーマンで説明します。入会金0円・1コマ（60分）から。相談だけでも大丈夫です。</p>
        <a class="btn btn-primary" href="/?service={cta}#contact">{cta_label}</a>
      </aside>
      <p class="small-note">※ この記事は一般的な学習の進め方を説明したものです。試験の制度・日程は変わることがあるため、最新の情報は主催者の公式サイトでご確認ください。</p>
    </div>
  </article>
  <section class="bg-soft" aria-labelledby="related-heading">
    <div class="container">
      <div class="sec-head"><span class="sec-en">Column</span><h2 class="sec-title" id="related-heading">ほかのコラム</h2></div>
      <ul class="column-list">
{related}
      </ul>
    </div>
  </section>
</main>
<!--@footer-->
</body>
</html>
"""

def card(m):
    return f'        <li><a href="/column/{m["slug"]}"><b>{esc(m["title"])}</b><span>{esc(m["description"])}</span></a></li>'

def date_ja(d):
    y, mo, da = d.split("-")
    return f"{int(y)}年{int(mo)}月{int(da)}日"

if articles:
    (out_dir / "column").mkdir(exist_ok=True)
for m in articles:
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "簿記合格ナビ", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "コラム", "item": SITE + "/column"},
            {"@type": "ListItem", "position": 3, "name": m["title"], "item": f'{SITE}/column/{m["slug"]}'}]},
        {"@type": "Article", "headline": m["title"], "description": m["description"],
         "datePublished": m["date"], "dateModified": m.get("updated", m["date"]), "inLanguage": "ja",
         "mainEntityOfPage": f'{SITE}/column/{m["slug"]}', "image": SITE + "/ogp.png",
         "author": {"@type": "Person", "name": "有村稜斗"},
         "publisher": {"@type": "EducationalOrganization", "name": "簿記合格ナビ", "url": SITE + "/"}}]}
    page = ARTICLE.format(title=esc(m["title"]), description=esc(m["description"]), slug=m["slug"], date=m["date"],
                          date_ja=date_ja(m["date"]), lead=m["lead"], body=m["body"], cta=m["cta"], cta_label=esc(m["cta_label"]),
                          jsonld=json.dumps(ld, ensure_ascii=False, indent=2),
                          related="\n".join(card(o) for o in articles if o is not m))
    (out_dir / "column" / f'{m["slug"]}.html').write_text(expand(page), encoding="utf-8")
    print("built", f'column/{m["slug"]}.html')

if articles:
    INDEX = """<!DOCTYPE html>
<html lang="ja">
<head>
<!--@head-->
  <title>簿記の学習コラム｜つまずきやすい論点の解説｜簿記合格ナビ</title>
  <meta name="description" content="日商簿記3級・2級の学習でつまずきやすい論点や、試験方式の違い、早稲田会計研究科の出願書類について、進め方を解説するコラムです。" />
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large" />
  <link rel="canonical" href="{{SITE}}/column" />
  <meta property="og:url" content="{{SITE}}/column" />
  <meta property="og:title" content="簿記の学習コラム｜簿記合格ナビ" />
  <meta property="og:description" content="日商簿記の学習でつまずきやすい論点の解説と、学習の進め方。" />
  <meta name="twitter:title" content="簿記の学習コラム｜簿記合格ナビ" />
  <meta name="twitter:description" content="日商簿記の学習でつまずきやすい論点の解説と、学習の進め方。" />
  <script type="application/ld+json">
  {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
    {"@type": "ListItem", "position": 1, "name": "簿記合格ナビ", "item": "{{SITE}}/"},
    {"@type": "ListItem", "position": 2, "name": "コラム", "item": "{{SITE}}/column"}]}
  </script>
</head>
<body>
<!--@header-->
<main id="main">
  <nav class="breadcrumb container" aria-label="パンくずリスト"><ol><li><a href="/">ホーム</a></li><li aria-current="page">コラム</li></ol></nav>
  <section class="sub-hero" aria-labelledby="column-title">
    <div class="container">
      <div class="sec-head"><span class="sec-en">Column</span><h1 class="sec-title" id="column-title">簿記の学習コラム</h1>
      <p class="sec-desc">独学で手が止まりやすい論点と、学習の進め方をまとめています。</p></div>
      <ul class="column-list">
%s
      </ul>
    </div>
  </section>
</main>
<!--@footer-->
</body>
</html>
"""
    (out_dir / "column" / "index.html").write_text(expand(INDEX.replace("%s", "\n".join(card(m) for m in articles))), encoding="utf-8")
    print("built column/index.html")

for f in sorted((root / "src/root").iterdir()):
    text = f.read_text(encoding="utf-8")
    if f.name == "sitemap.xml" and articles:
        latest = max(m.get("updated", m["date"]) for m in articles)
        urls = f"  <url><loc>{{{{SITE}}}}/column</loc><lastmod>{latest}</lastmod></url>\n" + "".join(
            f'  <url><loc>{{{{SITE}}}}/column/{m["slug"]}</loc><lastmod>{m.get("updated", m["date"])}</lastmod></url>\n' for m in articles)
        text = text.replace("</urlset>", urls + "</urlset>")
    (out_dir / f.name).write_text(text.replace("{{SITE}}", SITE), encoding="utf-8")
    print("built", f.name)
