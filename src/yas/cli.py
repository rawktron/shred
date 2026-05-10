#!/usr/bin/env python3
"""YAS: Yet Another static site generator.

Design goals:
- editable Markdown source
- TOML frontmatter only (+++ ... +++)
- Jinja2 templates
- no Node, no npm, no Hugo, no Astro

Run: yas
Output: dist/
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import textwrap
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin
from xml.sax.saxutils import escape as xml_escape

import mistune
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

# Raw HTML is deliberate here: content is local/trusted, not user-submitted.
markdown = mistune.create_markdown(escape=False, plugins=["strikethrough", "table", "url"])

DEFAULT_SITE: dict[str, Any] = {
    "title": "Untitled Site",
    "description": "",
    "base_url": "",
    "og_image": "",
    "language": "en",
}


@dataclass(frozen=True)
class SitePaths:
    root: Path
    content: Path
    templates: Path
    static: Path
    dist: Path
    site_config: Path

    @classmethod
    def from_root(cls, root: Path | str | None = None) -> "SitePaths":
        site_root = Path(root or ".").expanduser().resolve()
        return cls(
            root=site_root,
            content=site_root / "content",
            templates=site_root / "templates",
            static=site_root / "static",
            dist=site_root / "dist",
            site_config=site_root / "site.toml",
        )


@dataclass
class Entry:
    """One Markdown content file after frontmatter/body rendering."""

    slug: str
    collection: str
    source_path: Path
    body: str
    html: Markup
    text: str
    data: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = "") -> Any:
        return self.data.get(key, default)

    def __getattr__(self, key: str) -> Any:
        if key in self.data:
            return self.data[key]
        raise AttributeError(key)

    @property
    def title(self) -> str:
        return str(self.data.get("title") or self.slug.replace("-", " ").title())

    @property
    def kind(self) -> str:
        fallback = self.collection[:-1] if self.collection.endswith("s") else self.collection
        return str(self.data.get("kind") or fallback)

    @property
    def image(self) -> str:
        return str(self.data.get("image") or self.data.get("cover") or "")

    @property
    def url(self) -> str:
        if self.get("url"):
            return normalize_url(str(self.get("url")))
        if self.collection == "pages":
            if self.slug in {"home", "index"}:
                return "/"
            return f"/{self.slug}/"
        return f"/{self.collection}/{self.slug}/"


def load_site_config(paths: SitePaths) -> dict[str, Any]:
    site = dict(DEFAULT_SITE)
    if paths.site_config.exists():
        loaded = tomllib.loads(paths.site_config.read_text(encoding="utf-8"))
        # Allow either flat config or [site] table.
        if "site" in loaded and isinstance(loaded["site"], dict):
            site.update(loaded["site"])
        else:
            site.update(loaded)
    return site


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, Any], str]:
    """Parse TOML frontmatter only.

    Files may omit frontmatter, but if they use frontmatter it must be fenced with +++.
    No YAML legacy mode. No accidental colon soup.
    """
    text = text.replace("\r\n", "\n")
    if not text.startswith("+++\n"):
        return {}, text

    end = text.find("\n+++", 4)
    if end < 0:
        raise ValueError(f"Unclosed TOML frontmatter in {path}")

    raw = text[4:end].strip()
    body = text[end + len("\n+++") :].lstrip("\n")
    try:
        meta = tomllib.loads(raw) if raw else {}
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid TOML frontmatter in {path}: {exc}") from exc
    return meta, body


def render_markdown(body: str) -> tuple[Markup, str]:
    html = markdown(body or "")
    text = re.sub(r"<[^>]+>", " ", str(html))
    text = re.sub(r"\s+", " ", text).strip()
    return Markup(html), text


def read_entry(path: Path, collection: str) -> Entry:
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"), path)
    slug = str(meta.get("slug") or path.stem)
    html, text = render_markdown(body)
    return Entry(slug=slug, collection=collection, source_path=path, body=body, html=html, text=text, data=meta)


def sort_entries(entries: Iterable[Entry]) -> list[Entry]:
    def key(e: Entry) -> tuple[int, str, str]:
        order = e.get("order", 9999)
        try:
            order_i = int(order)
        except Exception:
            order_i = 9999
        date = str(e.get("date") or "")
        return (order_i, date, e.slug)

    return sorted(entries, key=key)


def load_collections(paths: SitePaths) -> dict[str, list[Entry]]:
    collections: dict[str, list[Entry]] = {}
    if not paths.content.exists():
        return collections
    for folder in sorted(p for p in paths.content.iterdir() if p.is_dir()):
        entries = [read_entry(p, folder.name) for p in sorted(folder.glob("*.md"))]
        collections[folder.name] = sort_entries(entries)
    return collections


def collection(collections: dict[str, list[Entry]], name: str) -> list[Entry]:
    return collections.get(name, [])


def find_page(collections: dict[str, list[Entry]], slug: str) -> Entry | None:
    for entry in collection(collections, "pages"):
        if entry.slug == slug:
            return entry
    return None


def page_map(collections: dict[str, list[Entry]]) -> dict[str, Entry]:
    return {entry.slug: entry for entry in collection(collections, "pages")}


def normalize_url(value: str) -> str:
    url = value.strip() or "/"
    return url if url.startswith("/") else f"/{url}"


def output_path_for_url(url: str) -> str:
    url = normalize_url(url)
    if url == "/":
        return "index.html"
    path = url.lstrip("/")
    if url.endswith("/"):
        return f"{path}index.html"
    if Path(path).suffix:
        return path
    return f"{path}/index.html"


def split_list(value: Any, sep: str = "|") -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value).split(sep) if part.strip()]


def pair_list(value: Any, sep: str = "|") -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for chunk in split_list(value, sep):
        if "|" in chunk:
            left, right = chunk.split("|", 1)
        elif "=" in chunk:
            left, right = chunk.split("=", 1)
        else:
            continue
        pairs.append((left.strip(), right.strip()))
    return pairs


def md_inline(value: Any) -> Markup:
    """Render small Markdown snippets and remove wrapping paragraph tags."""
    rendered = str(markdown(str(value or "").strip()))
    rendered = rendered.strip()
    if rendered.startswith("<p>") and rendered.endswith("</p>"):
        rendered = rendered[3:-4]
    return Markup(rendered)


def side_item(value: Any) -> Markup:
    text = str(value or "")
    if " — " in text:
        left, right = text.split(" — ", 1)
        return Markup(f"<b>{left}</b> — {right}")
    return Markup(text)


def group_by(items: Iterable[Any], key: str, default: Any = "") -> list[tuple[Any, list[Any]]]:
    groups: list[tuple[Any, list[Any]]] = []
    for item in items:
        if isinstance(item, Entry):
            value = item.get(key, default)
        elif isinstance(item, dict):
            value = item.get(key, default)
        else:
            value = getattr(item, key, default)
        if not groups or groups[-1][0] != value:
            groups.append((value, []))
        groups[-1][1].append(item)
    return groups


def short_date(value: Any) -> str:
    text = str(value or "")
    return text[:10] if len(text) >= 10 else text


def summary(entry: Entry, max_len: int = 170) -> str:
    raw = str(entry.get("summary") or entry.get("description") or entry.get("lede") or entry.text or "")
    raw = re.sub(r"\s+", " ", raw).strip()
    if len(raw) <= max_len:
        return raw
    return raw[: max_len - 1].rsplit(" ", 1)[0] + "…"


def build_env(paths: SitePaths) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(paths.templates)),
        autoescape=select_autoescape(["html", "xml"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["md_inline"] = md_inline
    env.filters["split_list"] = split_list
    env.filters["pair_list"] = pair_list
    env.filters["side_item"] = side_item
    env.filters["group_by"] = group_by
    env.filters["short_date"] = short_date
    return env


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_static(paths: SitePaths) -> None:
    if paths.dist.exists():
        shutil.rmtree(paths.dist)
    paths.dist.mkdir(parents=True)
    if paths.static.exists():
        for item in paths.static.iterdir():
            dest = paths.dist / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)


def template_exists(env: Environment, template: str) -> bool:
    return template in env.list_templates()


def base_context(site: dict[str, Any], collections: dict[str, list[Entry]], current_url: str = "/") -> dict[str, Any]:
    pages = page_map(collections)
    context: dict[str, Any] = {
        "site": site,
        "collections": collections,
        "pages": pages,
        "collection": lambda name: collection(collections, name),
        "page": lambda slug: pages.get(slug),
        "summary": summary,
        "current_url": normalize_url(current_url),
    }
    # Convenience for tiny templates: {{ posts }} instead of {{ collection("posts") }}.
    context.update(collections)
    return context


def render_page(paths: SitePaths, env: Environment, template: str, url: str, **context: Any) -> str:
    site = context.get("site", DEFAULT_SITE)
    route = normalize_url(url)
    context.setdefault("current_url", route)
    context.setdefault("page_title", site.get("title") or DEFAULT_SITE["title"])
    context.setdefault("description", site.get("description") or DEFAULT_SITE["description"])
    context.setdefault("og_image", site.get("og_image") or DEFAULT_SITE["og_image"])
    html = env.get_template(template).render(**context)
    write_file(paths.dist / output_path_for_url(route), html)
    return route


def absolute_url(site: dict[str, Any], path: str) -> str:
    return urljoin(str(site.get("base_url", "")).rstrip("/") + "/", path.lstrip("/"))


def write_sitemap(paths: SitePaths, site: dict[str, Any], routes: list[str]) -> None:
    if not site.get("base_url"):
        return
    now = datetime.now(timezone.utc).date().isoformat()
    urls = "\n".join(
        f"  <url><loc>{xml_escape(absolute_url(site, route))}</loc><lastmod>{now}</lastmod></url>" for route in routes
    )
    write_file(
        paths.dist / "sitemap.xml",
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n',
    )


def build(root: Path | str | None = None) -> None:
    paths = SitePaths.from_root(root)
    site = load_site_config(paths)
    collections = load_collections(paths)
    env = build_env(paths)
    copy_static(paths)

    routes: list[str] = []
    seen: set[str] = set()

    def add_route(route: str) -> None:
        if route not in seen:
            seen.add(route)
            routes.append(route)

    def render(template: str, url: str, **context: Any) -> None:
        route = normalize_url(url)
        render_context = base_context(site, collections, route)
        render_context.update(context)
        add_route(render_page(paths, env, template, route, **render_context))

    for entry in collection(collections, "pages"):
        if entry.get("render", True) is False:
            continue
        if entry.get("template"):
            template = str(entry.get("template"))
        elif entry.slug in {"home", "index"} and template_exists(env, "index.html"):
            template = "index.html"
        elif template_exists(env, f"{entry.slug}.html"):
            template = f"{entry.slug}.html"
        elif template_exists(env, "page.html"):
            template = "page.html"
        else:
            continue
        render(
            template,
            entry.url,
            entry=entry,
            page_title=entry.get("page_title") or entry.title,
            description=summary(entry),
            og_image=entry.image or site.get("og_image", ""),
        )

    if "/" not in seen and template_exists(env, "index.html"):
        render("index.html", "/")

    for name, entries in collections.items():
        if name == "pages":
            continue
        index_template = f"{name}.html"
        if template_exists(env, index_template):
            render(
                index_template,
                f"/{name}/",
                collection_name=name,
                entries=entries,
                items=entries,
                page_title=f"{name.replace('-', ' ').title()} — {site.get('title', DEFAULT_SITE['title'])}",
                description=site.get("description", ""),
                og_image=site.get("og_image", ""),
            )
        for entry in entries:
            if entry.get("render", True) is False:
                continue
            template = str(entry.get("template") or "")
            if not template:
                if template_exists(env, f"{name}-entry.html"):
                    template = f"{name}-entry.html"
                elif template_exists(env, "entry.html"):
                    template = "entry.html"
            if not template:
                continue
            render(
                template,
                entry.url,
                entry=entry,
                page_title=entry.get("page_title") or f"{entry.title} — {site.get('title', DEFAULT_SITE['title'])}",
                description=summary(entry),
                og_image=entry.image or site.get("og_image", ""),
            )

    if template_exists(env, "404.html"):
        render(
            "404.html",
            "/404.html",
            page_title=f"404 — {site.get('title', DEFAULT_SITE['title'])}",
            description="Page not found.",
        )

    write_sitemap(paths, site, [route for route in routes if route != "/404.html"])
    print(f"Built {len(routes)} pages into {paths.dist.relative_to(paths.root)}/")


def new_entry(collection_name: str, slug: str, title: str, root: Path | str | None = None) -> None:
    """Tiny convenience command: create content/foo/bar.md from a title."""
    paths = SitePaths.from_root(root)
    target = paths.content / collection_name / f"{slug}.md"
    if target.exists():
        raise SystemExit(f"Already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    escaped_title = title.replace('"', '\\"')
    target.write_text(
        textwrap.dedent(
            f'''\
            +++
            title = "{escaped_title}"
            slug = "{slug}"
            order = 999
            +++

            Write the thing here.
            '''
        ),
        encoding="utf-8",
    )
    print(f"Created {target.relative_to(paths.root)}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="YAS: Yet Another static site generator.")
    parser.add_argument("--root", default=".", help="site root containing content/, templates/, static/, and site.toml")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("build", help="Build the site into dist/")
    n = sub.add_parser("new", help="Create a new Markdown content file")
    n.add_argument("collection", help="content collection, e.g. posts/projects/notes")
    n.add_argument("slug", help="filename slug, e.g. fang")
    n.add_argument("title", help="human title")

    args = parser.parse_args(argv)
    if args.command in {None, "build"}:
        build(args.root)
    elif args.command == "new":
        new_entry(args.collection, args.slug, args.title, args.root)
    else:
        parser.error("unknown command")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
