# AGENTS.md -- conda-completion coding guidelines

## Project structure

- The package provides one conda subcommand (`conda completion`) with
  subcommands: `generate`, `install`, `uninstall`, `init`.

- This is a hybrid Python/Rust project. Python handles conda plugin
  registration, argparse introspection, and CLI orchestration. Rust
  handles the hot-path completion engine (`_conda_completer`) that runs
  on every TAB press.

- CLI modules live under `conda_completion/cli/`. Shell script
  generators are split by tier: `shell/` (Tier 1: bash, zsh,
  PowerShell -- fully tested in CI) and `contrib/` (Tier 2: fish --
  community-tested, best-effort).

- The Rust binary crate lives under `packages/conda-completer/`.
  Its Python wrapper (binary finder) is at
  `packages/conda-completer/python/conda_completer/__init__.py`.

- Tests mirror the source structure. Tests for
  `conda_completion/cli/generate.py` live in
  `tests/cli/test_generate.py`.

## Local development

- Bootstrap with pixi: `pixi install` sets up Python, Rust toolchain,
  and all dev dependencies.
- Build the Rust binary: `pixi run build` (release) or
  `pixi run build-debug` (debug).
- Run tests: `pixi run test`.
- Run all checks: `pixi run check` (lint + format + typecheck + clippy).
- Verify an end-to-end flow: `conda completion generate` then
  `conda completion init bash` to see the generated script.

## Imports

- Use relative imports for all intra-package references.
- Inline (lazy) imports are reserved for `plugin.py` hooks (loaded on
  every `conda` invocation), `__main__.py`, and `cli/main.py`
  subcommand dispatch. Everywhere else, imports belong at the top of
  the module.

## Dependencies

- Minimize the dependency graph. The Python side depends on `conda`,
  `conda-completer`, `platformdirs`, and `msgpack`.
- The Rust binary uses minimal crates: `serde`, `rmp-serde`, `toml`,
  `serde-saphyr`, `fs-err`. No rattler crates or heavy frameworks.
- Pin minimum versions in `pyproject.toml` (e.g., `"conda >=25.1"`),
  not exact versions.
- All packaging and dependency management goes through pixi. Never use
  `pip install` directly. Add dependencies to `pyproject.toml` and run
  `pixi install` to sync the environment.

## Typing and linting

- All code must be typed using modern annotations (`str | None` not
  `Optional[str]`, `list[str]` not `List[str]`).
- Use `ty` for type checking and `ruff` for linting and formatting.
  Both are configured in `pyproject.toml`.
- Use `from __future__ import annotations` in all modules.

## Code structure

- Prefer methods on existing classes over module-level private helpers.
- Do not use section comments (`# --- Helpers ---`,
  `# === Public API ===`) to group functions or tests.
- Comments should explain non-obvious intent, trade-offs, or
  constraints. Do not narrate what the code already says.

## Error handling

- All conda-completion exceptions inherit from `CondaCompletionError`
  (which inherits from conda's `CondaError`). Each exception class
  sets `error_message` and `hints` (a list of actionable suggestions).
- User-facing messages should use the file name (`completion.msgpack`)
  rather than internal concepts (`manifest`). Internal binary names
  (`_conda_completer`) should never appear in error messages.
- The `_maybe_regenerate` hook in `plugin.py` must never crash conda.
  It catches all exceptions but logs permission errors and I/O failures
  at warning level (not debug) so users can diagnose problems.

## Conda integration

- The plugin registers via `pluggy` hooks (`conda_subcommands`,
  `conda_post_commands`) and the `[project.entry-points.conda]`
  entry point.
- `plugin.py` must keep module-level imports minimal (only `hookimpl`
  and type imports). Everything else is lazily imported inside hook
  functions to keep the overhead under 1 ms on every `conda`
  invocation.
- The `conda_post_commands` hook triggers manifest regeneration after
  `install`, `remove`, and `update` commands when the set of
  registered plugins has changed.
- Subcommands silently accept `--json` (via argparse `SUPPRESS`) to
  avoid crashing when users pass `--json` globally.

## Testing

- Tests are plain `pytest` functions. No `unittest.TestCase` or
  class-based test grouping.
- Never use `unittest.mock`, `MagicMock`, `patch`, `Mock`, or any
  other `mock` library. Use `pytest` native fixtures (`tmp_path`,
  `monkeypatch`, `capsys`) and real fakes.
- Use `pytest.mark.parametrize` extensively.
- Put shared setup in fixtures in `conftest.py`.
- After changes, always run `pixi run test` and `pixi run check`.

## Rust conventions

- Run `cargo fmt` and `cargo clippy` before committing Rust changes.
  `pixi run clippy` runs clippy with `-D warnings`.
- Keep the dependency count minimal. Every new crate must be justified
  by a clear need that stdlib or existing deps cannot cover.
- Binary size target: release build should be under 1.5 MB. The release
  profile uses LTO, opt-level z, and strip.
- Performance target: static completions under 5 ms (cache hit),
  under 15 ms on cache miss.
- Use `&str` comparisons instead of allocating Strings for lookups.
  Prefer `HashSet` over `Vec` when checking membership.

## Lockfile maintenance

- After any change to `pyproject.toml` that affects pixi metadata,
  run `pixi lock` and commit the updated `pixi.lock`.

## Documentation

- Docs use Sphinx with `conda-sphinx-theme`, `myst-parser`, and
  `sphinx-design`.
- Follow the Diataxis framework: tutorials, how-to guides, reference,
  and explanation sections.

## Pull request and issue descriptions

- Write PR and issue bodies as one line per paragraph or bullet. Let
  GitHub wrap them in the browser. Do not hard-wrap prose.
