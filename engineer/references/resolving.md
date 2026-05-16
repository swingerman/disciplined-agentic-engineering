# Resolving the methodology root

Every DAE skill's first step is to locate the project's methodology root and
read its manifest. Skills do this by running the resolver script — they do not
hand-walk the directory tree or hand-parse the manifest.

## How

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dae_resolve.py [START_DIR]
```

`START_DIR` defaults to the current directory. The script walks up to find
`.engineer/manifest.yml`, parses it, validates it, and prints JSON:

```json
{
  "methodology_root": "/abs/path",
  "manifest_path": "/abs/path/.engineer/manifest.yml",
  "manifest": { ... },
  "valid": true,
  "errors": [],
  "warnings": []
}
```

## Exit codes — what the skill does

- **0** — manifest found and valid. Use `methodology_root` and `manifest` from the JSON.
- **1** — manifest found but **invalid**. Surface `errors` to the user and stop; recommend `/engineer.consistency-check --project` or fixing the manifest. Don't proceed against a broken manifest.
- **2** — **no manifest found**. The project isn't DAE-onboarded. Stop and point the user to `/engineer.onboard`.
- **3** — usage error.

## Notes

- The resolver is stdlib-only — no PyYAML or other dependency.
- `--validate-only` prints errors/warnings to stderr instead of the JSON.
- `onboard` is the one skill that does NOT resolve first — it *creates* the manifest. Its gap-check mode does read an existing one.
