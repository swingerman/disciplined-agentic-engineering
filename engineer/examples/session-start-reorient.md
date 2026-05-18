# Example: auto-reorient on context compaction

Optional project config. When Claude Code compacts the context, this hook nudges
the agent to run `/engineer.reorient` before continuing feature work.

Add to the project's `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": ".claude/hooks/reorient-nudge.sh" }
        ]
      }
    ]
  }
}
```

Create `.claude/hooks/reorient-nudge.sh` (make it executable — `chmod +x`):

```sh
#!/bin/sh
# SessionStart hook — on a context compaction, nudge a DAE re-anchor.
input=$(cat)
case "$input" in
  *'"source":"compact"'*)
    printf '%s' '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"Context was compacted. Run /engineer.reorient before continuing feature work — restore role, current checkpoint, exit criteria, and the next action."}}'
    ;;
esac
```

The hook script checks the `source` field itself, so it stays silent on normal
startup/resume and only fires after a compaction.
