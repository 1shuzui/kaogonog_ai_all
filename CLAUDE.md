<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **kaogonog_ai_all** (14002 symbols, 24272 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/kaogonog_ai_all/context` | Codebase overview, check index freshness |
| `gitnexus://repo/kaogonog_ai_all/clusters` | All functional areas |
| `gitnexus://repo/kaogonog_ai_all/processes` | All execution flows |
| `gitnexus://repo/kaogonog_ai_all/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

## Project Knowledge Base

Before changing behavior, start from the task-specific entry in
[docs/ai/README.md](docs/ai/README.md). It maps the authoritative implementation,
tests, API contracts, data rules, and operational checks for this repository.

High-value invariants:

- The three medical question banks are real **事业单位考试** assets; **医疗卫生面试**
  is a portal/position label, not a replacement `examCategory`.
- Question-bank source DOC/DOCX files live outside Git. Generated JSON is the
  runtime asset and must be regenerated through the importer, never hand-edited.
- Extended question metadata is persisted under `questions.keywords._meta`.
- `questionScore`, `appearanceScore`, and `effectiveFullScore` have distinct
  meanings. A valid `95 + 5` structure is not a score conflict, and a suite-scoped
  appearance score must only be counted once.

When documentation or code is changed, run `.venv/bin/python scripts/validate_project_docs.py`
in addition to the relevant tests and change detection.
