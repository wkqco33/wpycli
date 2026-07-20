from __future__ import annotations

from .context import ArgsValidator
from .errors import UsageError


def exact_args(n: int) -> ArgsValidator:
    def validator(args: list[str]) -> None:
        if len(args) != n:
            raise UsageError(f"accepts {n} arg(s), received {len(args)}")

    return validator


def min_args(n: int) -> ArgsValidator:
    def validator(args: list[str]) -> None:
        if len(args) < n:
            raise UsageError(f"requires at least {n} arg(s), received {len(args)}")

    return validator


def max_args(n: int) -> ArgsValidator:
    def validator(args: list[str]) -> None:
        if len(args) > n:
            raise UsageError(f"accepts at most {n} arg(s), received {len(args)}")

    return validator


def range_args(lo: int, hi: int) -> ArgsValidator:
    def validator(args: list[str]) -> None:
        if not (lo <= len(args) <= hi):
            raise UsageError(
                f"accepts between {lo} and {hi} arg(s), received {len(args)}"
            )

    return validator
