# Shred

A tiny no-bullshit static site generator.

Shred builds static sites from Markdown content, TOML frontmatter, Jinja2 templates, and a plain `static/` asset folder.

## Install

```bash
uv sync
```

## Build A Site

From a site repo that has `content/`, `templates/`, `static/`, and `site.toml`:

```bash
uv run shred
```

or from elsewhere:

```bash
uv run shred --root path/to/project
```

Output goes to the site's `dist/` directory.

## Create Content

```bash
uv run shred new posts hello "Hello"
```

This creates `content/posts/hello.md` in the selected site root.

## Content Format

Markdown files may include TOML frontmatter fenced with `+++`:

```md
+++
title = "Fang"
slug = "fang"
summary = "A tiny Python app bundler experiment."
tags = ["python", "rust", "packaging"]
order = 1
+++

Write the page body here.
```

No YAML frontmatter is supported. Entries without frontmatter render with a slug derived from the filename.

Set `render = false` in frontmatter to load an entry into the template context without writing it to `dist/`.

## site.toml

Top-level config for your site. Accepted keys under `[site]`:

```toml
[site]
title = "My Site"
description = "A site about things."
base_url = "https://example.com"
og_image = "/images/og.jpg"
language = "en"
```

## Template Context

Templates receive:

```txt
site              site.toml [site] values
collections       all content collections keyed by folder name
pages             content/pages entries by slug
collection(name)  helper for one collection
page(slug)        helper for one page
summary(entry)    plain-text excerpt (170 chars, truncates at word boundary)
entry             current Markdown entry, on entry pages
entries / items   entries in the collection, on collection index pages
current_url       route currently being rendered
page_title        resolved title for the current page
description       resolved description for the current page
og_image          resolved OG image path for the current page
```

Each collection is also injected directly by name so `{{ posts }}` works instead of `{{ collection("posts") }}`.

## Routing

Routing is convention-based and can be overridden with `url` in frontmatter:

```txt
content/pages/home.md  -> /
content/pages/about.md -> /about/
content/posts/hello.md -> /posts/hello/
url = "/work/fang/"    -> /work/fang/
```

## Template Naming

Shred picks templates by convention:

```txt
index.html            root / (also used if no pages/home.md exists)
page.html             fallback for content/pages/* entries
{slug}.html           page-specific template, e.g. about.html
{collection}.html     collection index, e.g. posts.html
{collection}-entry.html  entry page, e.g. posts-entry.html
entry.html            fallback entry page for any collection
404.html              written to dist/404.html
```

Set `template` in frontmatter to override any of the above.

## Jinja2 Filters

```txt
md_inline    render a Markdown snippet inline (strips wrapping <p>)
split_list   split a pipe-separated string (or list) into a list
pair_list    split into a list of (key, value) tuples
side_item    bold the left side of an em-dash pair
group_by     group a list of entries by a frontmatter key
short_date   truncate a date string to YYYY-MM-DD
```

## Sitemap

When `base_url` is set in `site.toml`, Shred writes `dist/sitemap.xml` automatically (excludes `/404.html`).

## Skill

A Claude Code skill for authoring Shred content is included in this repo:

```txt
skills/shred-content-author/SKILL.md
```

Install it with `claude skill install` from the repo root, or copy it to your Claude skills directory.

## Author

Pete Garcin — [rawktron.com](https://rawktron.com) · [@rawktron](https://github.com/rawktron)

## License

MIT — see [LICENSE](LICENSE).
