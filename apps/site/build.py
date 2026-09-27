"""Build the static website: apps/site/page.html -> apps/site/dist/.

page.html holds the page content (its <title>, styles, markup and script),
so the same file can be previewed as-is. This wraps it in a full HTML
document with the favicon and social-sharing tags, ready for any static
host (GitHub Pages, Cloudflare Pages, Netlify).

Usage: python apps/site/build.py
"""

import shutil
from pathlib import Path

SITE = Path(__file__).resolve().parent
DIST = SITE / "dist"
REPO = SITE.parent.parent

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="Termvera reads tenders and contracts, including scanned and stamped ones, and flags every liability, penalty and missing protection, cited to the clause and page. Runs entirely on your computer.">
<meta property="og:title" content="Termvera: the truth in every term">
<meta property="og:description" content="Tender and contract risk intelligence for contractors. Private by design: your documents never leave your laptop.">
<meta property="og:type" content="website">
<link rel="icon" href="favicon.ico">
"""


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    page = (SITE / "page.html").read_text(encoding="utf-8")
    # The page's own <title>, <link> and <style> belong in <head>; the rest is body.
    head_end = page.index("</style>") + len("</style>")
    document = f"{HEAD}{page[:head_end]}\n</head>\n<body>\n{page[head_end:]}\n</body>\n</html>\n"
    (DIST / "index.html").write_text(document, encoding="utf-8")
    shutil.copy2(REPO / "apps" / "desktop" / "termvera.ico", DIST / "favicon.ico")
    print(f"Built {DIST / 'index.html'}")


if __name__ == "__main__":
    main()
