# YAS

Yet Another SSG: a tiny Python static site generator.

YAS builds static sites from Markdown content, TOML frontmatter, Jinja2 templates, and a plain `static/` asset folder.

## Install

```bash
uv sync
```

## Build A Site

From a site repo that has `content/`, `templates/`, `static/`, and `site.toml`:

```bash
uv run yas
```

or from elsewhere:

```bash
uv run yas --root path/to/site
```

Output goes to the site's `dist/` directory.

## Create Content

```bash
uv run yas new posts hello "Hello"
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
+++

Write the page body here.
```

No YAML frontmatter is supported.

## Template Context

Templates receive:

```txt
site              site.toml [site] values
collections       all content collections
pages             content/pages entries by slug
collection(name)  helper for one collection
page(slug)        helper for one page
entry             current Markdown entry, on entry pages
current_url       route currently being rendered
```

## Routing

Routing is convention-based and can be overridden with `url` in frontmatter:

```txt
content/pages/home.md  -> /
content/pages/about.md -> /about/
content/posts/hello.md -> /posts/hello/
url = "/work/fang/"    -> /work/fang/
```

## Packaged Skill

The YAS content authoring skill is included as package data:

```txt
yas/skills/yas-content-author/SKILL.md
```
