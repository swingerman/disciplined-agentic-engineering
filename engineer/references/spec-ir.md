# The spec IR — `spec.md` → `.build/spec.json`

The acceptance pipeline runs on a JSON intermediate representation, not on the
markdown source. `spec.md` is the human source of truth; `.build/spec.json` is
the canonical IR every downstream consumer reads (Foundation Design Section 7).
The IR shape is adopted from Uncle Bob's
[Acceptance-Pipeline-Specification](https://github.com/unclebob/Acceptance-Pipeline-Specification).

## Producing the IR

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dae_gherkin.py SPEC_MD [OUT_JSON]
```

`atdd:atdd` (Checkpoint 3) produces `spec.md`; the parser produces
`features/NNN-slug/.build/spec.json` from it. Generators and the mutator read
the IR — they never re-parse `spec.md`. Stdlib-only, portable (Gherkin is a
standard — one parser serves every project).

Exit 0 = parsed; 1 = spec error; 2 = I/O error; 3 = usage.

## `spec.md` format

Standard Gherkin embedded in a markdown file:

- Recognised: `Feature:`, `Background:`, `Scenario:`, `Scenario Outline:`, step
  lines (`Given` / `When` / `Then` / `And`), `Examples:`, pipe-delimited tables.
- Parameters are `<name>` placeholders (`[A-Za-z0-9_]+`) inside step text.
- **Everything else is ignored** — markdown prose, headings, ``` fences. This
  lets a `spec.md` carry human description around the Gherkin.
- A leading markdown heading marker is stripped before matching, so both
  `## Scenario: X` and plain `Scenario: X` work. (Unlike Uncle Bob's `.feature`
  parser, `#` is NOT a comment here — in markdown it's a heading.)

## IR shape

```json
{
  "name": "Feature name",
  "background": [
    { "keyword": "Given", "text": "a configured project", "parameters": [] }
  ],
  "scenarios": [
    {
      "name": "Scenario name",
      "steps": [
        { "keyword": "Then", "text": "the image is <w> by <h>",
          "parameters": ["w", "h"] }
      ],
      "examples": [
        { "w": "1080", "h": "1080" }
      ]
    }
  ]
}
```

- **Feature** — `name`, `background` (step array; `[]` if none), `scenarios`.
- **Scenario** — `name`, `steps`, `examples` (`[]` if none).
- **Step** — `keyword` (Given/When/Then/And), `text`, `parameters` (in order of appearance, repeats kept).
- **Example** — a map of column name → value; **all values are strings**.

`Scenario:` and `Scenario Outline:` produce the same shape. A scenario without
examples runs once; one with examples runs once per row.

## Spec errors (exit 1)

- No `Feature:` declaration
- `Examples:` outside a scenario
- A step outside any background/scenario
- An examples data row whose cell count differs from the header

## Downstream

- **Generator** (project-specific, via `atdd`'s pipeline-builder) — IR → executable acceptance tests
- **Mutator** (`atdd:mutate`) — alters example values in the IR, regenerates, expects failure

## References

- [Acceptance-Pipeline-Specification](https://github.com/unclebob/Acceptance-Pipeline-Specification) — the portable pipeline + IR this adopts
- [DAE Foundation Design](https://www.notion.so/3585ecdee0e2811bbc67ff4913c03207) — Section 7, the acceptance pipeline alignment
