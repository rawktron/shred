---
name: shred-content-author
description: Use when converting notes, drafts, outlines, or pasted source material into Shred Markdown content files with TOML frontmatter.
---

# Shred Content Author

Create or update content files for a Shred project.

## Workflow

1. Inspect `content/` to discover the existing collections (each subdirectory is a collection).
2. Choose the right collection, or create a new one if none fits.
3. Create a kebab-case filename and `slug`.
4. Write TOML frontmatter fenced with `+++`.
5. Keep the body as plain Markdown.
6. Preserve the user's voice and mark uncertain fields with `needsReview = true`.

## Collections

Collections are whatever subdirectories exist under `content/` in the site repo. There are no fixed names — list `content/` first and use what you find. If no existing collection fits, create a new one with a clear, lowercase, plural name (e.g. `content/notes/`).

## Frontmatter

Use only fields supported by the site templates or clearly needed by the content.

```toml
+++
title = "Entry Title"
slug = "entry-title"
summary = "One short sentence."
needsReview = true
+++
```

Do not invent dates, links, tags, summaries, or classifications. If the source material is ambiguous, either omit the field or set `needsReview = true`.
