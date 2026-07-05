---
name: release
description: >-
  Cut a new release of reels-encoder-ai. Bumps __version__ in version.py,
  generates release notes from git history since the last tag, and prepares the
  annotated tag + GitHub release draft. Invoke as: /release <new-version>
  (e.g. /release 2.2.0). Semver only.
disable-model-invocation: true
---

# /release — version bump + release notes

Argument: `$ARGUMENTS` = the new version, semver `MAJOR.MINOR.PATCH`
(e.g. `2.2.0`). If empty, infer a sensible bump from the commit history since
the last tag (feat → minor, fix → patch) and confirm with the user before
proceeding.

The single source of truth for the version is `version.py`
(`__version__ = "X.Y.Z"`), imported by both the engine and the `ui` package.

## Steps

1. **Preflight — never release a dirty or failing tree.**
   ```bash
   git status --porcelain          # must be clean (or only intended changes)
   git describe --tags --abbrev=0   # last release tag
   python -m pytest enhance/ ui/ -q # tests must pass
   ```
   If the tree is dirty or tests fail, stop and report — do not tag.

2. **Bump the version** in `version.py` — edit only the `__version__` line to
   the new value. Leave `__app_name__` / `__tagline__` untouched.

3. **Generate release notes** from commits since the last tag:
   ```bash
   git log <last-tag>..HEAD --no-merges --pretty="- %s"
   ```
   Group into **Features / Fixes / Docs / Internal** by conventional-commit
   prefix. Lead with a one-line summary of the release's theme.

4. **Commit, tag, and draft the release** (confirm the message with the user
   first):
   ```bash
   git add version.py
   git commit -m "release: vX.Y.Z"
   git tag -a vX.Y.Z -m "vX.Y.Z"
   ```
   Then draft the GitHub release with the generated notes:
   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z" --notes-file <notes> --draft
   ```
   Use `--draft` so the user reviews before publishing. Do **not** push or
   publish without explicit confirmation.

5. **Report** the new version, the tag, the notes, and the draft-release URL.
