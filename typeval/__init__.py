import re
import sys
from inspect import isclass
from types import NoneType
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Tuple, Union

if sys.version_info < (3, 9):
    from typing_extensions import Annotated, get_args, get_origin, get_type_hints
else:
    from typing import Annotated, get_args, get_origin, get_type_hints

import annotated_types as at
from pydantic_core import SchemaValidator
from pydantic_core import ValidationError  # noqa: F401

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


_SIMPLE_TYPES: Dict[type, str] = {
    int: "int",
    float: "float",
    bool: "bool",
    str: "str",
}


def _build_schema(tp: type) -> Mapping[str, Any]:
    tp, constraints = _unpack_type(tp)
    schema: Schema = {}
    origin = get_origin(tp)
    if tp in _SIMPLE_TYPES:
        schema["type"] = _SIMPLE_TYPES[tp]
        schema.update(compile_constraints(constraints))
        return schema
    origin = get_origin(tp)
    if origin is Union:
        schema["type"] = "union"
        schema["choices"] = [_build_schema(tp_arg) for tp_arg in get_args(tp)]
        return schema
    elif origin in (List, list):  # TODO: lenient subclass
        schema["type"] = "list"
        schema["items"] = _build_schema(next(iter(get_args(tp))))
    elif origin in (Dict, dict):
        schema["type"] = "dict"
        keys, values = get_args(tp)
        schema["keys"] = _build_schema(keys)
        schema["values"] = _build_schema(values)
    else:
        # assume model for now
        if not isclass(tp):
            raise TypeError(f"Unknown type {tp}")
        schema["type"] = "model-class"
        schema["model"] = {
            "type": "model",
            "fields": {
                k: _build_schema(v)
                for k, v in get_type_hints(tp, include_extras=True).items()
            },
        }
        schema["class"] = tp
    return schema


def build_validator(tp: type) -> SchemaValidator:
    schema = _build_schema(tp)
    return SchemaValidator(dict(schema))
