from typing import Any, Callable, Dict, Iterable, Mapping, Type

import annotated_types as at

CompiledConstraint = Mapping[str, Any]


def _compile_gt(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.Gt)
    return {"gt": constraint.gt}


def _compile_lt(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.Lt)
    return {"lt": constraint.lt}


def _compile_ge(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.Ge)
    return {"ge": constraint.ge}


def _compile_le(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.Le)
    return {"le": constraint.le}


def _compile_multiple_of(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.MultipleOf)
    return {"multiple_of": constraint.multiple_of}


def _compile_regex(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.Regex)
    return {"pattern": constraint.regex_pattern}


def _compile_len(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.Len)
    res = {"min_length": constraint.min_inclusive}
    if constraint.max_exclusive is not None:
        res["max_length"] = constraint.max_exclusive
    return res


_KNOWN_PREDICATES: Dict[Any, CompiledConstraint] = {
    str.islower: {"to_lower": True},
}


def _compile_predicate(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.Predicate)
    if constraint.func not in _KNOWN_PREDICATES:
        raise TypeError(f"Unknown predicate {constraint.func}")
    return _KNOWN_PREDICATES[constraint.func]


_KNOWN_CONSTRAINTS: Dict[
    Type[at.BaseMetadata], Callable[[at.BaseMetadata], CompiledConstraint]
] = {
    at.Le: _compile_le,
    at.Ge: _compile_ge,
    at.Lt: _compile_lt,
    at.Gt: _compile_gt,
    at.Len: _compile_len,
    at.MultipleOf: _compile_multiple_of,
    at.Regex: _compile_regex,
    at.Predicate: _compile_predicate,
}


def compile_constraints(constraints: Iterable[at.BaseMetadata]) -> CompiledConstraint:
    res: "Dict[str, Any]" = {}
    for constraint in constraints:
        if type(constraint) not in _KNOWN_CONSTRAINTS:
            raise TypeError(f"Unknown constraint type {constraint.__class__.__name__}")
        res.update(_KNOWN_CONSTRAINTS[type(constraint)](constraint))
    return res
