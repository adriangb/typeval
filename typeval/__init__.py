import re
import sys
from inspect import isclass
from types import NoneType
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    Mapping,
    Set,
    Tuple,
    Union,
)

if sys.version_info < (3, 9):
    from typing_extensions import Annotated, get_args, get_origin, get_type_hints
else:
    from typing import Annotated, get_args, get_origin, get_type_hints

import annotated_types as at
from pydantic_core import ValidationError  # noqa: F401
from pydantic_core import SchemaValidator

from typeval._constraints import compile_constraints

__all__ = [
    "ValidationError",
    "build_validator",
]


def _get_constraints(args: Iterable[Any]) -> Iterator[at.BaseMetadata]:
    for arg in args:
        if isinstance(arg, re.Pattern):
            arg = at.Regex(arg.pattern, arg.flags)  # type: ignore[arg-type]
        if isinstance(arg, slice):
            start, stop = arg.start, arg.stop
            if not isinstance(start, int):
                raise TypeError(
                    f"{arg} is an invalid length slice, start must be an integer"
                )
            if not isinstance(stop, (NoneType, int)):
                raise TypeError(
                    f"{arg} is an invalid length slice, stop must be an integer or None"
                )
            arg = at.Len(start or 0, stop)  # type: ignore[arg-type]
        if isinstance(arg, at.BaseMetadata):
            if isinstance(arg, at.Interval):
                for case in arg:
                    yield case
            else:
                yield arg


def _unpack_type(tp: type) -> Tuple[type, Iterator[at.BaseMetadata]]:
    origin = get_origin(tp)
    if origin is not Annotated:
        return (tp, iter(()))
    args = iter(get_args(tp))
    tp = next(args)
    return (tp, _get_constraints(args))


Schema = Dict[str, Any]


_SIMPLE_TYPES: Dict[Any, str] = {
    int: "int",
    float: "float",
    bool: "bool",
    str: "str",
    type(None): "none",
    None: "none",
    Any: "any",
}


def _build_schema(
    tp: type, seen: Set[type], recursive_containers: Set[type]
) -> Mapping[str, Any]:
    tp, constraints = _unpack_type(tp)
    schema: Schema = {}
    origin = get_origin(tp)
    schema.update(compile_constraints(constraints))
    if tp in _SIMPLE_TYPES:
        schema["type"] = _SIMPLE_TYPES[tp]
        return schema
    origin = get_origin(tp)
    if origin is Literal:
        args = get_args(tp)
        schema["type"] = "literal"
        schema["expected"] = args
    elif origin is Union:
        args = get_args(tp)
        if len(args) == 2 and None in args:
            schema["type"] = "optional"
            schema["schema"] = _build_schema(
                next(iter(arg for arg in args if arg is not None)),
                seen,
                recursive_containers,
            )
            return schema
        else:
            schema["type"] = "union"
            schema["choices"] = [
                _build_schema(tp_arg, seen, recursive_containers)
                for tp_arg in get_args(tp)
            ]
            return schema
    elif isinstance(origin, type) and issubclass(origin, List):
        schema["type"] = "list"
        schema["items"] = _build_schema(
            next(iter(get_args(tp))), seen, recursive_containers
        )
        if "min_length" in schema:
            schema["min_items"] = schema.pop("min_length")
        if "max_length" in schema:
            schema["max_items"] = schema.pop("max_length")
    elif isinstance(origin, type) and issubclass(origin, Set):
        schema["type"] = "set"
        schema["items"] = _build_schema(
            next(iter(get_args(tp))), seen, recursive_containers
        )
        if "min_length" in schema:
            schema["min_items"] = schema.pop("min_length")
        if "max_length" in schema:
            schema["max_items"] = schema.pop("max_length")
    elif isinstance(origin, type) and issubclass(origin, Dict):
        schema["type"] = "dict"
        keys, values = get_args(tp)
        schema["keys"] = _build_schema(keys, seen, recursive_containers)
        schema["values"] = _build_schema(values, seen, recursive_containers)
        if "min_length" in schema:
            schema["min_items"] = schema.pop("min_length")
        if "max_length" in schema:
            schema["max_items"] = schema.pop("max_length")
    else:
        # assume class
        if not isclass(tp):
            raise TypeError(f"Unknown type {tp}")
        if tp in seen:
            recursive_containers.add(tp)
            schema["type"] = "recursive-ref"
            schema["name"] = str(id(tp))
            return schema
        seen.add(tp)
        schema["type"] = "model-class"
        schema["model"] = {
            "type": "model",
            "fields": {
                k: _build_schema(v, seen, recursive_containers)
                for k, v in get_type_hints(tp, include_extras=True).items()
            },
        }
        schema["class_type"] = tp
        if tp in recursive_containers:
            schema = {
                "type": "recursive-container",
                "name": str(id(tp)),
                "schema": schema,
            }
    return schema


def build_validator(tp: type) -> SchemaValidator:
    schema = _build_schema(tp, set(), set())
    return SchemaValidator(dict(schema))  # type: ignore[arg-type]
