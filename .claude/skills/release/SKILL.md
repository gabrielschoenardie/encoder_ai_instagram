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

3. **Generate release notes** from commits since the last tag and **write them
   to a file** (the release step consumes this file):
   ```bash
   git log <last-tag>..HEAD --no-merges --pretty="- %s" > /tmp/release-notes.md
   ```
   Then rewrite `/tmp/release-notes.md` grouped into **Features / Fixes / Docs /
   Internal** by conventional-commit prefix, led by a one-line summary of the
   release's theme.

4. **Commit and tag** (confirm the message with the user first):
   ```bash
   git add version.py
   git commit -m "release: vX.Y.Z"
   git tag -a vX.Y.Z -m "vX.Y.Z"
   ```

5. **Push, then draft the release.** `gh release create` needs the tagged commit
   on the remote first, so push the branch and the tag *before* creating the
   release (confirm with the user before pushing — this is the outward step):
   ```bash
   git push origin HEAD          # push the release commit
   git push origin vX.Y.Z        # push the tag it points at
   gh release create vX.Y.Z --title "vX.Y.Z" --notes-file /tmp/release-notes.md --draft
   ```
   `--draft` so the user reviews before publishing. Do **not** publish (or push)
   without explicit confirmation.

6. **Report** the new version, the tag, the notes, and the draft-release URL.
