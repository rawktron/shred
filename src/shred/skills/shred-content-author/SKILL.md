---
name: shred-content-author
description: Use when converting notes, drafts, outlines, or pasted source material into Shred Markdown content files with TOML frontmatter.
---

# Shred Content Author

Create or update content files for a Shred project.

## Workflow

1. Choose the target collection under `content/`.
2. Create a kebab-case filename and `slug`.
3. Write TOML frontmatter fenced with `+++`.
4. Keep the body as plain Markdown.
5. Preserve the user's voice and mark uncertain fields with `needsReview = true`.

## Collections

- `content/books/`
- `content/features/`
- `content/pages/`
- `content/practices/`
- `content/projects/`
- `content/repos/`
- `content/writing/`

## Frontmatter

Use only fields supported by the site templates or clearly needed by the content.

```toml
+++
title = "Project Title"
slug = "project-title"
summary = "One short sentence."
needsReview = true
+++
```

Do not invent dates, links, tags, summaries, or classifications. If the source material is ambiguous, either omit the field or set `needsReview = true`.
