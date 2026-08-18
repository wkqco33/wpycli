from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

FlagParser = Callable[[str], Any]


def _parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {raw!r}")


_PARSERS: dict[str, FlagParser] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": _parse_bool,
    # Used when count flags are explicitly passed with values (e.g., --verbose=2).
    "count": int,
}

_METAVARS: dict[str, str] = {
    "str": "STRING",
    "int": "INT",
    "float": "FLOAT",
    "bool": "BOOL",
    "count": "COUNT",
}

# Flag kinds that never consume a following argv token (`--flag value`).
_NO_VALUE_KINDS = {"bool", "count"}


@dataclass(frozen=True, slots=True)
class Flag:
    name: str
    kind: str = "str"
    help: str = ""
    default: Any = None
    shorthand: str | None = None
    required: bool = False
    choices: tuple[Any, ...] | None = None
    hidden: bool = False

    def __post_init__(self) -> None:
        if (
            not self.name
            or re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_-]*", self.name) is None
        ):
            raise ValueError("flag name must be a shell-safe long name")
        if self.kind not in _PARSERS:
            raise ValueError(f"unsupported flag kind: {self.kind!r}")
        if self.shorthand is not None and (
            len(self.shorthand) != 1
            or re.fullmatch(r"[A-Za-z0-9_]", self.shorthand) is None
        ):
            raise ValueError("flag shorthand must be a shell-safe single character")
        if (
            self.choices
            and self.default is not None
            and self.default not in self.choices
        ):
            raise ValueError(
                f"default {self.default!r} for --{self.name} is not one of {self.choices!r}"
            )

    @property
    def takes_value(self) -> bool:
        return self.kind not in _NO_VALUE_KINDS

    @property
    def metavar(self) -> str:
        return _METAVARS[self.kind]

    def convert(self, raw: str) -> Any:
        return _PARSERS[self.kind](raw)


class FlagSet:
    def __init__(self) -> None:
        self._flags: dict[str, Flag] = {}
        self._shorthands: dict[str, str] = {}

    def add(self, flag: Flag) -> Flag:
        if flag.name in self._flags:
            raise ValueError(f"duplicate flag name: {flag.name}")
        if flag.shorthand and flag.shorthand in self._shorthands:
            raise ValueError(f"duplicate flag shorthand: {flag.shorthand}")
        self._flags[flag.name] = flag
        if flag.shorthand:
            self._shorthands[flag.shorthand] = flag.name
        return flag

    def create(
        self,
        name: str,
        *,
        kind: str = "str",
        help: str = "",
        default: Any = None,
        shorthand: str | None = None,
        required: bool = False,
        choices: Sequence[Any] | None = None,
        hidden: bool = False,
    ) -> Flag:
        return self.add(
            Flag(
                name=name,
                kind=kind,
                help=help,
                default=default,
                shorthand=shorthand,
                required=required,
                choices=tuple(choices) if choices is not None else None,
                hidden=hidden,
            )
        )

    def get(self, name: str) -> Flag | None:
        return self._flags.get(name)

    def get_short(self, shorthand: str) -> Flag | None:
        name = self._shorthands.get(shorthand)
        if name is None:
            return None
        return self._flags[name]

    def defaults(self) -> dict[str, Any]:
        return {flag.name: flag.default for flag in self}

    def __iter__(self):
        return iter(self._flags.values())

    def __bool__(self) -> bool:
        return bool(self._flags)
