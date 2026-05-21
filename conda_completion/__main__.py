"""Allow running via ``python -m conda_completion``."""

from __future__ import annotations


def main(args: list[str] | None = None) -> None:
    """Entry point for ``python -m conda_completion``."""
    from .cli.main import configure_parser, execute

    parser = configure_parser()
    parsed = parser.parse_args(args)
    raise SystemExit(execute(parsed))


if __name__ == "__main__":
    main()
