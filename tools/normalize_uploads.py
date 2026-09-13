#!/usr/bin/env python3
"""
Give Keystatic-uploaded photos real filenames.

Why this exists
---------------
The Keystatic admin lets the owner drag a photo straight into a gallery, which
is the point: no files, no git. But for an image field nested inside an array,
Keystatic names the uploaded file after the field's *position*, not the file the
owner picked, so a drop lands as:

    public/assets/img/gallery/sections/0/images/8/src.jpg

That is bad twice over. A filename is a real (if minor) image-search signal, and
"src.jpg" says nothing, while the caption next to it usually says exactly who is
in the picture. Worse, the name encodes an array index: delete or reorder a
photo and a later upload can land on a path an existing entry still points at,
silently swapping two pictures.

So: after the owner uploads, run this. It renames each machine-named file to a
slug built from its own caption (falling back to alt text, then the section
title), moves it to the flat gallery directory, and rewrites the path in the
YAML. Names become stable and descriptive, and the index collision goes away.

    python3 tools/normalize_uploads.py [--dry-run]

Then run tools/optimize_images.py so the renamed files get their variants.

The rewrite is textual on purpose: Keystatic owns the formatting of these files,
and a YAML round-trip would reflow them into a needless diff.
"""
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
PUBLIC = os.path.join(ROOT, "public")

# A path Keystatic generated from a field position rather than a real filename:
# any assets/img/... path with a numeric directory segment in it.
MACHINE = re.compile(r"assets/img/[A-Za-z0-9._/-]*?/\d+/[A-Za-z0-9._/-]*\.(?:jpe?g|png)")
# `key: "value"` or `key: value`, and `- key: value` inside a list item.
FIELD = re.compile(r"^\s*-?\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$")


def slugify(text, fallback="photo"):
    s = re.sub(r"[^\w\s-]", "", (text or "").lower()).strip()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:60] or fallback


def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def describe(lines, i):
    """Caption-ish text from the list item that owns the image on line i.

    Scoped to that one item deliberately: a plain nearest-match search picks up
    the neighbouring photo's caption and names the file after the wrong picture.
    Keystatic writes `- src:` first, so the item's own fields follow it until the
    next sibling `- ` at the same indent, or a dedent.
    """
    indent = len(lines[i]) - len(lines[i].lstrip())
    item = {}
    for j in range(i, len(lines)):
        line = lines[j]
        if not line.strip():
            continue
        here = len(line) - len(line.lstrip())
        if j > i and (here < indent or (here == indent and line.lstrip().startswith("- "))):
            break
        m = FIELD.match(line)
        if m:
            item.setdefault(m.group(1), unquote(m.group(2)))
    for key in ("cap", "alt", "title"):
        if item.get(key):
            return item[key]
    return ""


def main():
    dry = "--dry-run" in sys.argv
    taken = set()
    moves = []       # (old_rel, new_rel)
    edits = 0

    yamls = sorted(
        os.path.join(CONTENT, f) for f in os.listdir(CONTENT) if f.endswith(".yaml")
    )
    # Reserve every path already in use so a new name never lands on one.
    for path in yamls:
        for m in re.finditer(r"assets/img/[A-Za-z0-9._/-]+\.(?:jpe?g|png)", open(path, encoding="utf-8").read()):
            taken.add(m.group(0))

    for path in yamls:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines(keepends=True)
        changed = False

        for i, line in enumerate(lines):
            m = MACHINE.search(line)
            if not m:
                continue
            old_rel = m.group(0)
            ext = os.path.splitext(old_rel)[1].lower()
            base = slugify(describe(lines, i))

            new_rel = f"assets/img/gallery/{base}{ext}"
            n = 2
            while new_rel in taken:
                new_rel = f"assets/img/gallery/{base}-{n}{ext}"
                n += 1
            taken.add(new_rel)

            lines[i] = line.replace(old_rel, new_rel)
            changed = True
            edits += 1
            moves.append((old_rel, new_rel))

        if changed and not dry:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("".join(lines))

    for old_rel, new_rel in moves:
        src = os.path.join(PUBLIC, old_rel)
        dst = os.path.join(PUBLIC, new_rel)
        status = "ok"
        if not os.path.isfile(src):
            status = "MISSING on disk, YAML updated anyway"
        elif not dry:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
        print(f"  {old_rel}\n    -> {new_rel}  ({status})")

    # Keystatic's nested upload folders are empty once the files move out.
    # Re-check with listdir rather than os.walk's dirnames: walking bottom-up
    # still hands back the listing captured before the children were removed,
    # so a parent that just became empty would look occupied and survive.
    if not dry:
        imgroot = os.path.join(PUBLIC, "assets", "img")
        for dirpath, _, _ in os.walk(imgroot, topdown=False):
            if dirpath == imgroot:
                continue
            try:
                if not os.listdir(dirpath):
                    os.rmdir(dirpath)
            except OSError:
                pass

    if not edits:
        print("No machine-named uploads found; nothing to do.")
        return 0
    print(f"\n{edits} upload(s) renamed{' (dry run, nothing written)' if dry else ''}.")
    if not dry:
        print("Next: python3 tools/optimize_images.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
