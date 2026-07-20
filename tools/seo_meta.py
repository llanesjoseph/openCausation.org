#!/usr/bin/env python3
"""Insert SEO metadata and JSON-LD into the static <head> of each page.

Tags go in the real <head> (not <helmet>, which is hoisted at runtime by
support.js) so crawlers see them without executing JavaScript.
Idempotent: strips any managed tags it previously inserted before re-inserting.

The JSON-LD asserts only what the site itself states: Causation.com, Inc. is
named as operator in the privacy policy and terms. Pages carry no bylines or
publication dates, so they are typed WebPage rather than Article, which would
require author and datePublished.
"""
import json
import re
import pathlib

SITE = "https://opencausation.org"
# Social card: 1200x630, the size Facebook/LinkedIn/X render without cropping.
OG_IMAGE = f"{SITE}/og-image.png"
OG_IMAGE_W, OG_IMAGE_H = 1200, 630
# Organization mark, sized to its largest on-page use (32px) at 4x for retina.
LOGO = f"{SITE}/logo.png"
LOGO_W, LOGO_H = 192, 128

# Cloudflare Web Analytics — cookieless, no individual-visitor tracking, no
# fingerprinting. One beacon, same on every page. Invisible to visitors.
CF_BEACON = (
    '<!-- Cloudflare Web Analytics -->'
    '<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js" '
    'data-cf-beacon=\'{"token": "d5ecb426727649298c78e9302dbe1616"}\'></script>'
)
ORG_ID = f"{SITE}/#organization"
SITE_ID = f"{SITE}/#website"

SITE_DESC = (
    "OpenCausation.org is a free, noncommercial educational resource presenting a "
    "structured, evidence-based methodology for evaluating medical causation."
)

# Trail of (nav label, clean path) from Home to the page's parent.
# Labels match the site's own nav — note /references is labelled "Sources".
BREADCRUMBS = {
    "fundamentals": [("Home", "/")],
    "methodology": [("Home", "/")],
    "bradford-hill": [("Home", "/")],
    "legal-standards": [("Home", "/")],
    "examples": [("Home", "/")],
    "carpal-tunnel": [("Home", "/"), ("Examples", "/examples")],
    "low-back-pain": [("Home", "/"), ("Examples", "/examples")],
    "rotator-cuff": [("Home", "/"), ("Examples", "/examples")],
    "glossary": [("Home", "/")],
    "references": [("Home", "/")],
    "about": [("Home", "/")],
    "contributors": [("Home", "/")],
    "terms-of-use": [("Home", "/")],
    "privacy-policy": [("Home", "/")],
}

# Leaf label shown as the final breadcrumb crumb (nav wording where it exists).
CRUMB_LABEL = {
    "fundamentals": "Fundamentals",
    "methodology": "The Method",
    "bradford-hill": "Bradford Hill",
    "legal-standards": "The Legal Standards",
    "examples": "Examples",
    "carpal-tunnel": "Carpal Tunnel Syndrome",
    "low-back-pain": "Low Back Pain",
    "rotator-cuff": "Rotator Cuff Syndrome",
    "glossary": "Glossary",
    "references": "Sources",
    "about": "About",
    "contributors": "Contributors",
    "terms-of-use": "Terms of Use",
    "privacy-policy": "Privacy Policy",
}

# slug -> (clean_url_path, title, description)
PAGES = {
    "index": (
        "/",
        "OpenCausation.org | Evidence-Based Medical Causation Methodology",
        "OpenCausation.org is a free, noncommercial educational resource presenting a "
        "structured, evidence-based methodology for evaluating medical causation.",
    ),
    "fundamentals": (
        "/fundamentals",
        "The Fundamentals of Causation Analysis — OpenCausation.org",
        "Four foundational ideas behind a credible causation analysis: evidence over "
        "assumption, disciplined reasoning, and awareness of the limits of what the "
        "facts can support.",
    ),
    "methodology": (
        "/methodology",
        "The Method: Six-Step Causation Analysis — OpenCausation.org",
        "The structured, evidence-based six-step causation methodology, grounded in "
        "Chapter 4 of the AMA Guides to the Evaluation of Disease and Injury Causation, "
        "2nd edition.",
    ),
    "bradford-hill": (
        "/bradford-hill",
        "The Bradford Hill Viewpoints — OpenCausation.org",
        "Bradford Hill's nine viewpoints for assessing whether an observed association "
        "may be causal — each weighed on the evidence, never tallied as a checklist or "
        "scoring system.",
    ),
    "legal-standards": (
        "/legal-standards",
        "The Legal Standards of Causation — OpenCausation.org",
        "Burdens of proof, the relative-risk 2.0 threshold, and the admissibility of "
        "expert testimony — how the probabilities produced by science translate into "
        "legal decisions.",
    ),
    "examples": (
        "/examples",
        "Case Examples — OpenCausation.org",
        "Three worked examples — carpal tunnel syndrome, low back pain, and rotator cuff "
        "syndrome — showing how one neutral method reaches different conclusions on "
        "different evidence.",
    ),
    "carpal-tunnel": (
        "/carpal-tunnel",
        "Carpal Tunnel Syndrome — OpenCausation.org",
        "Causation and apportionment of median nerve entrapment at the wrist: a worked "
        "example of the evidence-based causation method applied to carpal tunnel "
        "syndrome.",
    ),
    "low-back-pain": (
        "/low-back-pain",
        "Low Back Pain — OpenCausation.org",
        "Causation and apportionment of nonspecific low back pain: a worked example of "
        "the evidence-based causation method applied to a common multifactorial "
        "condition.",
    ),
    "rotator-cuff": (
        "/rotator-cuff",
        "Rotator Cuff Syndrome — OpenCausation.org",
        "Causation and apportionment of tendinopathy, impingement, and rotator cuff "
        "tears: a worked example of the evidence-based causation method.",
    ),
    "glossary": (
        "/glossary",
        "Glossary — OpenCausation.org",
        "Key terms in medical causation analysis — from association, confounding, and "
        "relative risk to apportionment and the Bradford Hill viewpoints.",
    ),
    "references": (
        "/references",
        "References — OpenCausation.org",
        "The primary sources behind the OpenCausation methodology, including the AMA "
        "Guides to the Evaluation of Disease and Injury Causation, 2nd edition (2014).",
    ),
    "about": (
        "/about",
        "About — OpenCausation.org",
        "About OpenCausation.org: a free, noncommercial educational resource on "
        "evidence-based medical causation methodology, and the people behind it.",
    ),
    "contributors": (
        "/contributors",
        "Contributors — OpenCausation.org",
        "The clinicians, causation methodologists, and technologists who develop and "
        "review OpenCausation.org's neutral, evidence-based causation methodology.",
    ),
    "terms-of-use": (
        "/terms-of-use",
        "Terms of Use — OpenCausation.org",
        "Terms of Use for OpenCausation.org, an open, noncommercial educational resource "
        "operated by Causation.com, Inc.",
    ),
    "privacy-policy": (
        "/privacy-policy",
        "Privacy Policy — OpenCausation.org",
        "Privacy Policy for OpenCausation.org, an open, noncommercial educational "
        "resource operated by Causation.com, Inc.",
    ),
}

# Tags this script owns; removed from <head> before re-inserting so reruns don't stack.
MANAGED = re.compile(
    r'[ \t]*(?:'
    r'<title>.*?</title>'
    r'|<meta\s+name="description"[^>]*>'
    r'|<meta\s+name="robots"[^>]*>'
    r'|<link\s+rel="canonical"[^>]*>'
    r'|<meta\s+property="og:[^"]*"[^>]*>'
    r'|<meta\s+name="twitter:[^"]*"[^>]*>'
    r'|<script type="application/ld\+json">.*?</script>'
    r'|<!-- Cloudflare Web Analytics --><script[^>]*data-cf-beacon[^>]*></script>'
    r')[ \t]*\n?',
    re.S | re.I,
)


def abs_url(path: str) -> str:
    return SITE + "/" if path == "/" else SITE + path


def jsonld(slug: str, path: str, title: str, desc: str) -> str:
    """Build the JSON-LD @graph for one page."""
    url = abs_url(path)
    page_id = f"{url}#webpage"

    page = {
        "@type": "WebPage",
        "@id": page_id,
        "url": url,
        "name": title,
        "description": desc,
        "isPartOf": {"@id": SITE_ID},
        "publisher": {"@id": ORG_ID},
        "inLanguage": "en-US",
        "isAccessibleForFree": True,
    }

    graph = []

    if slug == "index":
        graph.append({
            "@type": "Organization",
            "@id": ORG_ID,
            "name": "Causation.com, Inc.",
            "url": SITE + "/",
            "logo": {
                "@type": "ImageObject",
                "url": LOGO,
                "width": LOGO_W,
                "height": LOGO_H,
            },
        })
        graph.append({
            "@type": "WebSite",
            "@id": SITE_ID,
            "url": SITE + "/",
            "name": "OpenCausation.org",
            "description": SITE_DESC,
            "publisher": {"@id": ORG_ID},
            "inLanguage": "en-US",
        })
    else:
        trail = BREADCRUMBS.get(slug, [])
        items = [
            {"@type": "ListItem", "position": i, "name": name, "item": abs_url(p)}
            for i, (name, p) in enumerate(trail, start=1)
        ]
        items.append({
            "@type": "ListItem",
            "position": len(items) + 1,
            "name": CRUMB_LABEL.get(slug, title),
            "item": url,
        })
        crumb_id = f"{url}#breadcrumb"
        page["breadcrumb"] = {"@id": crumb_id}
        graph.append({
            "@type": "BreadcrumbList",
            "@id": crumb_id,
            "itemListElement": items,
        })

    graph.append(page)
    payload = {"@context": "https://schema.org", "@graph": graph}
    body = json.dumps(payload, indent=2, ensure_ascii=False)
    return f'<script type="application/ld+json">\n{body}\n</script>\n'


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def block(path: str, title: str, desc: str) -> str:
    url = SITE + ("" if path == "/" else path) + ("/" if path == "/" else "")
    t, d = esc(title), esc(desc)
    return "\n".join([
        f"<title>{t}</title>",
        f'<meta name="description" content="{d}">',
        f'<link rel="canonical" href="{url}">',
        '<meta name="robots" content="index, follow, max-image-preview:large">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="OpenCausation.org">',
        f'<meta property="og:title" content="{t}">',
        f'<meta property="og:description" content="{d}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{OG_IMAGE}">',
        f'<meta property="og:image:width" content="{OG_IMAGE_W}">',
        f'<meta property="og:image:height" content="{OG_IMAGE_H}">',
        f'<meta property="og:image:alt" content="OpenCausation.org — Causation, determined by science.">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{t}">',
        f'<meta name="twitter:description" content="{d}">',
        f'<meta name="twitter:image" content="{OG_IMAGE}">',
        CF_BEACON,
    ]) + "\n"


def main() -> int:
    # public/ sits next to tools/, so resolve relative to this file rather than cwd.
    pub = pathlib.Path(__file__).resolve().parent.parent / "public"
    if not pub.is_dir():
        print(f"error: {pub} not found")
        return 1
    changed = 0
    for slug, (path, title, desc) in PAGES.items():
        f = pub / f"{slug}.html"
        src = f.read_text()

        head_m = re.search(r"<head>(.*?)</head>", src, re.S | re.I)
        if not head_m:
            print(f"  !! {slug}.html: no <head> found — SKIPPED")
            continue

        head = MANAGED.sub("", head_m.group(1))

        payload = block(path, title, desc) + jsonld(slug, path, title, desc)

        # Insert before the support.js script so metadata leads the head.
        script_m = re.search(r'[ \t]*<script src="\./support\.js"></script>', head)
        if script_m:
            head = head[:script_m.start()] + payload + head[script_m.start():].lstrip("\n")
        else:
            head = head.rstrip("\n") + "\n" + payload

        new = src[:head_m.start(1)] + head + src[head_m.end(1):]
        if new != src:
            f.write_text(new)
            changed += 1
            print(f"  ok  {slug}.html")
    print(f"\n{changed} file(s) updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
