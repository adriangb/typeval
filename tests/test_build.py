from dataclasses import dataclass
from typing import Annotated, List, Union

import annotated_types as at
import pytest

from typeval import ValidationError, build_validator


def test_build_validator() -> None:
    @dataclass
    class MyModel:
        a_list: Annotated[List[Annotated[float, at.Ge(0), at.Lt(100)]], at.Len(1, 10)]
        a_union: Union[
            Annotated[int, at.Ge(0), at.Lt(100)], Annotated[float, at.Ge(100)]
        ]

    validator = build_validator(MyModel)
    assert validator.validate_python({"a_list": [1], "a_union": 101}) == MyModel(
        [1.0], 101.0
    )
    assert validator.validate_python({"a_list": [1], "a_union": 99}) == MyModel(
        [1.0], 99
    )


def test_build_validator_nested() -> None:
    @dataclass
    class Inner:
        foo: Annotated[str, at.Len(1)]

    @dataclass
    class Outer:
        inner: Inner

    validator = build_validator(Outer)
    assert validator.validate_python({"inner": {"foo": "abc"}}) == Outer(Inner("abc"))


@dataclass
class RecursiveModel:
    inner: "Annotated[List[RecursiveModel], at.Len(1)]"


@pytest.mark.xfail(raises=RecursionError, reason="Not yet implemented")
def test_build_validator_recursive() -> None:
    validator = build_validator(RecursiveModel)
    assert validator.validate_python({"inner": [{"inner": []}]}) == RecursiveModel(
        [RecursiveModel([])]
    )


def test_validation_failure() -> None:
    @dataclass
    class MyModel:
        foo: Annotated[str, at.Regex(r"^abc$")]

    validator = build_validator(MyModel)
    with pytest.raises(ValidationError):
        validator.validate_python({"foo": "abcd"})
