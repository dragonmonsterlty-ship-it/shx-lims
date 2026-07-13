from collections.abc import Iterable


ALL_MODULES = ("lims", "refstd")
MODULE_VALUES = frozenset(ALL_MODULES)


def normalize_modules(values: Iterable[str]) -> list[str]:
    modules = list(values)
    if not modules:
        raise ValueError("at least one module is required")
    if len(modules) != len(set(modules)):
        raise ValueError("modules must not contain duplicates")
    if not set(modules).issubset(MODULE_VALUES):
        raise ValueError("modules must be a non-empty subset of: lims, refstd")
    return [module for module in ALL_MODULES if module in modules]


def parse_modules(value: str) -> list[str]:
    return normalize_modules(part.strip() for part in value.split(",") if part.strip())


def serialize_modules(values: Iterable[str]) -> str:
    return ",".join(normalize_modules(values))
