from typing import Any, Callable, Dict, Iterable, Mapping, Type

import annotated_types as at

CompiledConstraint = Mapping[str, Any]


def compile_gt(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.Gt)
    return {"gt": constraint.gt}


def compile_lt(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.Lt)
    return {"lt": constraint.lt}


def compile_ge(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.Ge)
    return {"ge": constraint.ge}


def compile_le(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.Le)
    return {"le": constraint.le}


def compile_multiple_of(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.MultipleOf)
    return {"multiple_of": constraint.multiple_of}


def compile_len(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.Len)
    res = {"min_length": constraint.min_inclusive}
    if constraint.max_exclusive is not None:
        res["max_length"] = constraint.max_exclusive
    return res


KNOWN_PREDICATES: Dict[Any, CompiledConstraint] = {
    str.islower: {"to_lower": True},
}


def compile_predicate(constraint: at.BaseMetadata) -> CompiledConstraint:
    assert isinstance(constraint, at.Predicate)
    if constraint.func not in KNOWN_PREDICATES:
        raise TypeError(f"Unknown predicate {constraint.func}")
    return KNOWN_PREDICATES[constraint.func]


KNOWN_CONSTRAINTS: Dict[
    Type[at.BaseMetadata], Callable[[at.BaseMetadata], CompiledConstraint]
] = {
    at.Le: compile_le,
    at.Ge: compile_ge,
    at.Lt: compile_lt,
    at.Gt: compile_gt,
    at.Len: compile_len,
    at.MultipleOf: compile_multiple_of,
    at.Predicate: compile_predicate,
}


def compile_constraints(constraints: Iterable[at.BaseMetadata]) -> CompiledConstraint:
    res: "Dict[str, Any]" = {}
    for constraint in constraints:
        if type(constraint) not in KNOWN_CONSTRAINTS:
            raise TypeError(f"Unknown constraint type {constraint.__class__.__name__}")
        res.update(KNOWN_CONSTRAINTS[type(constraint)](constraint))
    return res
