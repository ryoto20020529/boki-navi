#!/usr/bin/env python3
"""サイトの自動チェック。PRごとに GitHub Actions でも実行する。

使い方: python3 tools/check.py
失敗（ERROR）が1件でもあれば終了コード1。警告（WARN）は表示のみ。
外部ライブラリは使わない（標準ライブラリのみ）。
"""
import html
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = re.search(r'SITE = "([^"]+)"', (ROOT / "tools/build.py").read_text(encoding="utf-8")).group(1)

errors, warns = [], []
def err(page, msg): errors.append(f"[{page}] {msg}")
def warn(page, msg): warns.append(f"[{page}] {msg}")

PAGES = sorted(p.name for p in (ROOT / "src/pages").glob("*.html"))   # 生成されるページ
COLUMN = sorted("column/" + p.name for p in (ROOT / "column").glob("*.html")) if (ROOT / "column").is_dir() else []   # コラム（src/articles から生成）
PAGES += COLUMN
PATHS = {p: "/" if p == "index.html" else "/column" if p == "column/index.html" else "/" + p[:-5] for p in PAGES}
LEGAL = ["tokushoho.html", "privacy.html", "terms.html"]       # 手書きの法務ページ
ALL = PAGES + LEGAL
read = lambda name: (ROOT / name).read_text(encoding="utf-8")
strip_tags = lambda s: re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]+>", "", s)))


# ---------- 1. 生成物が src/ の出力と一致している（直接編集の検知） ----------
def check_build_in_sync():
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run([sys.executable, str(ROOT / "tools/build.py"), "--out", tmp], capture_output=True, text=True)
        if r.returncode != 0:
            err("build", "tools/build.py が失敗しました: " + r.stderr.strip()[-200:])
            return
        built = set()
        for f in sorted(p for p in pathlib.Path(tmp).rglob("*") if p.is_file()):
            rel = f.relative_to(tmp).as_posix(); built.add(rel)
            if not (ROOT / rel).exists() or (ROOT / rel).read_text(encoding="utf-8") != f.read_text(encoding="utf-8"):
                err(rel, "生成物が src/ と一致しません。直接編集せず、src/ を編集して python3 tools/build.py を実行してください")
        for c in COLUMN:
            if c not in built:
                err(c, "元になる src/articles の記事がありません（不要な生成物なら削除してください）")


# ---------- 2. 料金の一致 ----------
def load_prices():
    js = read("assets/site.js")
    block = re.search(r"var PRICES = \{(.*?)\};", js, re.S).group(1)
    prices = {}
    for key, name, on, off in re.findall(r"(\w+):\s*\{\s*name:\s*'([^']+)',\s*online:\s*(\d+),\s*offline:\s*(\d+)", block):
        prices[key] = (name, int(on), int(off))
    return prices

def check_prices():
    prices = load_prices()
    if not prices:
        err("assets/site.js", "PRICES を読み取れません")
        return
    unit = {p for _, on, off in prices.values() for p in (on, off)}
    ok = {u * k for u in unit for k in range(1, 13)}          # 1〜12コマ分の合計は許容（月額例・プラン例）
    for page in ALL:
        s = read(page)
        body = re.sub(r"<(script|style)[\s\S]*?</\1>", "", s)
        # 仕訳の例（table.journal と直後の注記）の金額は、料金ではないので対象外
        body = re.sub(r'<table class="journal">[\s\S]*?</table>(\s*<p class="small-note">[\s\S]*?</p>)?', "", body)
        for m in re.finditer(r"¥\s*([\d,]{4,})|([\d,]{4,})円", body):
            n = int((m.group(1) or m.group(2)).replace(",", ""))
            if n not in ok and n != 50000:
                err(page, f"料金表にない金額 {n:,}円 があります（PRICES の単価×1〜12コマ以外）")
        for m in re.finditer(r'"price":\s*"(\d+)"', s):
            if int(m.group(1)) not in unit:
                err(page, f"JSON-LD の price {m.group(1)} が PRICES にありません")
    # 料金表の行ごとの一致（表の行に出る online/offline の組を PRICES と照合）
    pairs = {(on, off) for _, on, off in prices.values()}
    for page in PAGES:
        s = read(page)
        for on, off in re.findall(r'class="p col-online">¥([\d,]+)<span>/時</span></td><td class="p col-offline">¥([\d,]+)', s):
            if (int(on.replace(",", "")), int(off.replace(",", ""))) not in pairs:
                err(page, f"料金表の行 オンライン{on}/対面{off} が PRICES の組と一致しません")


# ---------- 3. FAQ（表示と構造化データ）の一致 ----------
def jsonld_blocks(s):
    out = []
    for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        out.append(json.loads(raw))
    return out

def flatten(blocks):
    for b in blocks:
        yield from b.get("@graph", [b])

def check_faq_and_jsonld():
    for page in PAGES:
        s = read(page)
        try:
            nodes = list(flatten(jsonld_blocks(s)))
        except json.JSONDecodeError as e:
            err(page, f"JSON-LD が壊れています: {e}")
            continue
        types = {n.get("@type") for n in nodes}
        if "BreadcrumbList" not in types and page != "index.html":
            err(page, "BreadcrumbList がありません")
        faq_ld = [(q["name"], strip_tags(q["acceptedAnswer"]["text"])) for n in nodes if n.get("@type") == "FAQPage" for q in n["mainEntity"]]
        faq_html = [(strip_tags(q), strip_tags(a)) for q, a in re.findall(r'<details><summary>(.*?)</summary><div class="a">(.*?)</div></details>', s, re.S)]
        if [q for q, _ in faq_ld] != [q for q, _ in faq_html]:
            err(page, "FAQ の質問が、表示と構造化データ（FAQPage）で一致しません")
        else:
            for (q, a1), (_, a2) in zip(faq_ld, faq_html):
                if strip_tags(a1) != a2:
                    err(page, f"FAQ『{q}』の回答が、表示と構造化データで一致しません")
        if not faq_html and not page.startswith("column/"):
            warn(page, "FAQ がありません")


# ---------- 4. title / description / canonical / H1 ----------
class Head(HTMLParser):
    def __init__(self):
        super().__init__(); self.h1 = 0; self.imgs_no_alt = 0; self.meta = {}; self.canonical = None; self.lang = None
    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag == "html": self.lang = a.get("lang")
        if tag == "h1": self.h1 += 1
        if tag == "img" and not a.get("alt") and a.get("alt") != "": self.imgs_no_alt += 1
        if tag == "meta":
            key = a.get("name") or a.get("property")
            if key: self.meta[key] = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical": self.canonical = a.get("href")

def check_meta():
    paths = PATHS
    for page in ALL:
        s = read(page); h = Head(); h.feed(s)
        title = re.search(r"<title>(.*?)</title>", s, re.S)
        if not title: err(page, "title がありません")
        elif len(title.group(1)) > 70: err(page, f"title が長すぎます（{len(title.group(1))}字）")
        if h.lang != "ja": err(page, "html の lang が ja ではありません")
        if h.h1 != 1 and page in PAGES: err(page, f"H1 が {h.h1} 個あります（1個にしてください）")
        if h.imgs_no_alt: err(page, f"alt のない画像が {h.imgs_no_alt} 個あります")
        if page in PAGES:
            d = h.meta.get("description", "")
            if not d: err(page, "meta description がありません")
            elif len(d) > 160: err(page, f"meta description が長すぎます（{len(d)}字）")
            if h.canonical != SITE + (paths[page] if paths[page] != "/" else "/"): err(page, f"canonical が想定と異なります: {h.canonical}")
            if h.meta.get("og:url") != h.canonical: err(page, "og:url が canonical と一致しません")
            if "noindex" in h.meta.get("robots", ""): err(page, "公開ページに noindex が付いています")
        else:
            if "noindex" not in h.meta.get("robots", ""): warn(page, "法務ページが noindex ではありません")
    titles = [re.search(r"<title>(.*?)</title>", read(p), re.S).group(1) for p in PAGES]
    if len(set(titles)) != len(titles): err("title", "title が重複しているページがあります")


# ---------- 5. 内部リンク・sitemap・robots ----------
def check_links():
    route = {v: k for k, v in PATHS.items()}
    route.update({"/tokushoho": "tokushoho.html", "/privacy": "privacy.html", "/terms": "terms.html"})
    ids = {p: set(re.findall(r'\bid="([^"]+)"', read(p))) for p in ALL}
    for page in ALL:
        for href in re.findall(r'href="([^"]+)"', read(page)):
            if re.match(r"(https?:|mailto:|tel:)", href) or href.startswith("data:"): continue
            path, _, frag = href.partition("#")
            path = path.split("?")[0]
            if path == "":
                target = page
            elif path.startswith("/assets/") or path in ("/favicon.svg", "/apple-touch-icon.png", "/ogp.png"):
                if not (ROOT / path.lstrip("/")).exists(): err(page, f"存在しないファイルへのリンク: {href}")
                continue
            elif path in route:
                target = route[path]
            else:
                err(page, f"リンク先が存在しません: {href}"); continue
            if frag and frag not in ids[target]:
                err(page, f"リンク先のアンカーが存在しません: {href}")
    sm = read("sitemap.xml"); locs = re.findall(r"<loc>([^<]+)</loc>", sm)
    want = {SITE + p for p in PATHS.values()}
    if set(locs) != want: err("sitemap.xml", f"sitemap の URL が公開ページと一致しません: {sorted(set(locs) ^ want)}")
    if f"Sitemap: {SITE}/sitemap.xml" not in read("robots.txt"): err("robots.txt", "Sitemap の行が SITE と一致しません")
    for p in PAGES:
        if p.startswith("column/") and p != "column/index.html": continue   # 記事は /column の一覧からリンクされる
        if p != "index.html" and PATHS[p] not in "".join(re.findall(r'href="([^"]+)"', read("index.html") + read("src/partials/footer.html"))):
            warn(p, "トップまたはフッターからリンクされていません")
    try:
        v = json.loads(read("vercel.json"))
        srcs = {r["source"] for r in v.get("redirects", [])}
        for gone in ("/toukei", "/actuary"):
            if gone not in srcs: err("vercel.json", f"削除済みページ {gone} のリダイレクトがありません")
    except json.JSONDecodeError as e:
        err("vercel.json", f"JSON が壊れています: {e}")


# ---------- 6. 使ってはいけない表現・古い情報 ----------
FORBIDDEN = [
    (r"統計検定", "取り扱い終了したコース名"), (r"アクチュアリー", "取り扱い終了したコース名"),
    (r"ryoto140529", "旧メールアドレス"), (r"東京都内", "旧対応エリア表記（東京・埼玉・神奈川に変更済み）"),
    (r"最短\d+日", "根拠のない期間の断定"), (r"必ず合格|絶対に?合格|100%合格|合格を保証します", "合格の断定・保証"),
    (r"合格率|合格者数|合格実績|満足度", "実績の数値（実在データがない）"), (r"No\.?\s?1|ナンバーワン|日本一|業界(最|NO)", "根拠のない最上級表現"),
    (r"登録講師は全員|講師陣は全員", "講師が在籍している前提の表現"),
    (r"fonts\.googleapis\.com|fonts\.gstatic\.com|googletagmanager|google-analytics", "外部への通信（プライバシーポリシーとCSPに未記載）"),
]
def check_forbidden():
    files = [ROOT / p for p in ALL] + list((ROOT / "src").rglob("*.html")) + [ROOT / "assets/site.js"]
    for f in files:
        s = re.sub(r"<!--.*?-->", "", f.read_text(encoding="utf-8"), flags=re.S)
        for pat, why in FORBIDDEN:
            for m in re.finditer(pat, s):
                err(str(f.relative_to(ROOT)), f"使用禁止の表現「{m.group(0)}」（{why}）")


# ---------- 7. フォームの初期表示（回帰テスト） ----------
def check_form_initial_state():
    s = read("index.html")
    for id_ in ["errorBar", "successView", "err-name", "err-email", "err-service", "err-message", "err-privacy"]:
        m = re.search(rf'<div[^>]*id="{id_}"[^>]*>(.*?)</div>', s, re.S)
        if not m: err("index.html", f"#{id_} が見つかりません"); continue
        tag = re.search(rf'<div[^>]*id="{id_}"[^>]*>', s).group(0)
        if "hidden" not in tag: err("index.html", f"#{id_} に hidden 属性がありません（初回表示で見えてしまいます）")
        if m.group(1).strip(): err("index.html", f"#{id_} の中に文言が書かれています（JSで必要なときだけ表示してください）")


# ---------- 8. 法務ページと実態の整合 ----------
def check_legal_consistency():
    tk, tm = read("tokushoho.html"), read("terms.html")
    for page, s in (("tokushoho.html", tk), ("terms.html", tm)):
        for name, on, off in load_prices().values():
            if f"{on:,}円" not in s: err(page, f"{name} のオンライン料金 {on:,}円 が記載されていません")
    if "wasecpa.academy@gmail.com" not in tk: err("tokushoho.html", "連絡先メールアドレスがありません")
    for kw in ("電話番号", "月初に前払い", "毎月5日", "1か月分まで", "未受講分は、全額返金", "提携・公認等の関係はありません", "別途お見積もり"):
        if kw not in tk: err("tokushoho.html", f"必須の記載「{kw}」がありません")
    for page in LEGAL:
        if "最終更新日：" not in read(page): err(page, "最終更新日がありません")
    # 支払期日などの細かい決まりは、規約と特商法の表記にだけ書く（トップ・コース・コラムには書かない）
    for page in PAGES:
        for m in re.finditer(r"前日までに(お振込|お支払|入金)|毎月\d+日まで|支払期日は|お支払い期限", read(page)):
            err(page, f"支払期日の記載「{m.group(0)}」があります。期日は利用規約と特商法の表記にだけ書いてください")


def main():
    for fn in (check_build_in_sync, check_prices, check_faq_and_jsonld, check_meta, check_links,
               check_forbidden, check_form_initial_state, check_legal_consistency):
        try: fn()
        except Exception as e: err(fn.__name__, f"チェック自体が失敗しました: {type(e).__name__}: {e}")
    for w in warns: print("WARN ", w)
    for e in errors: print("ERROR", e)
    print(f"\n{'NG' if errors else 'OK'}: ERROR {len(errors)} 件 / WARN {len(warns)} 件")
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
