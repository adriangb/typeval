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
from pydantic_core import SchemaValidator

from typeval._constraints import compile_constraints


def get_constraints(args: Iterable[Any]) -> Iterator[at.BaseMetadata]:
    for arg in args:
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


def unpack_type(tp: type) -> Tuple[type, Iterator[at.BaseMetadata]]:
    origin = get_origin(tp)
    if origin is not Annotated:
        return (tp, iter(()))
    args = iter(get_args(tp))
    tp = next(args)
    return (tp, get_constraints(args))


Schema = Dict[str, Any]


SIMPLE_TYPES: Dict[Any, str] = {
    int: "int",
    float: "float",
    bool: "bool",
    str: "str",
    type(None): "none",
    None: "none",
    Any: "any",
}


def build_schema(
    tp: type, seen: Set[type], recursive_containers: Set[type]
) -> Mapping[str, Any]:
    tp, constraints = unpack_type(tp)
    schema: Schema = {}
    origin = get_origin(tp)
    schema.update(compile_constraints(constraints))
    if tp in SIMPLE_TYPES:
        schema["type"] = SIMPLE_TYPES[tp]
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
            schema["schema"] = build_schema(
                next(iter(arg for arg in args if arg is not None)),
                seen,
                recursive_containers,
            )
            return schema
        else:
            schema["type"] = "union"
            schema["choices"] = [
                build_schema(tp_arg, seen, recursive_containers)
                for tp_arg in get_args(tp)
            ]
            return schema
    elif isinstance(origin, type) and issubclass(origin, List):
        schema["type"] = "list"
        schema["items_schema"] = build_schema(
            next(iter(get_args(tp))), seen, recursive_containers
        )
        if "min_length" in schema:
            schema["min_items"] = schema.pop("min_length")
        if "max_length" in schema:
            schema["max_items"] = schema.pop("max_length")
    elif isinstance(origin, type) and issubclass(origin, Set):
        schema["type"] = "set"
        schema["items_schema"] = build_schema(
            next(iter(get_args(tp))), seen, recursive_containers
        )
        if "min_length" in schema:
            schema["min_items"] = schema.pop("min_length")
        if "max_length" in schema:
            schema["max_items"] = schema.pop("max_length")
    elif isinstance(origin, type) and issubclass(origin, Dict):
        schema["type"] = "dict"
        keys, values = get_args(tp)
        schema["keys_schema"] = build_schema(keys, seen, recursive_containers)
        schema["values_schema"] = build_schema(values, seen, recursive_containers)
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
            schema["schema_ref"] = str(id(tp))
            return schema
        seen.add(tp)
        schema["type"] = "model-class"
        schema["schema"] = {
            "type": "typed-dict",
            "return_fields_set": True,
            "fields": {
                k: {"schema": build_schema(v, seen, recursive_containers)}
                for k, v in get_type_hints(tp, include_extras=True).items()
            },
        }
        schema["class_type"] = tp
        if tp in recursive_containers:
            schema["ref"] = str(id(tp))
    return schema


def build_validator(tp: type) -> SchemaValidator:
    schema = build_schema(tp, set(), set())
    return SchemaValidator(dict(schema))  # type: ignore[arg-type]
