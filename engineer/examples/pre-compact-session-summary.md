# Example: write the session log before context is compacted

Optional project config. Compaction is the moment session context is lost — and
it is exactly when "how will I pick this up?" gets asked. This hook nudges the
agent to write `session-log.md` *before* the compaction, so the pickup record
survives it.

The companion to `session-start-reorient.md`: this one saves state on the way
out, that one restores it on the way in. Running both is the point — either
alone leaves half the boundary uncovered.

Add to the project's `.claude/settings.json`:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          { "type": "command", "command": ".claude/hooks/session-summary-nudge.sh" }
        ]
      }
    ]
  }
}
```

Create `.claude/hooks/session-summary-nudge.sh` (make it executable — `chmod +x`):

```sh
#!/bin/sh
# PreCompact hook — capture the session log before context is summarized away.
printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":"Context is about to be compacted. If this session touched a DAE feature, run /engineer.session-summary FIRST so session-log.md carries the current state, the in-flight task, and the concrete next actions across the boundary."}}'
```

## Why a hook rather than a skill step

`session-summary` is per **session**, not per checkpoint. Auto-invoking it at
every checkpoint exit would append several entries per day to `session-log.md`
and make the file useless for its one job — being readable when you come back
cold. The genuine session boundaries are: the feature merged (handled inside
`post-merge`), the context compacted (this hook), and the human stopping
(a `Stop` hook, or just asking).

## Verifying it fires

```sh
echo '{}' | .claude/hooks/session-summary-nudge.sh
```

Should print the JSON above. If the hook is configured but nothing happens on
compaction, check the script is executable and the path in `settings.json` is
relative to the project root.
