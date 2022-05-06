from dataclasses import dataclass
from typing import Annotated, Any, Dict, List, Set, Union, Optional

import annotated_types as at
import pytest

from typeval import ValidationError, build_validator


def test_scalars() -> None:
    @dataclass
    class MyModel:
        a_float: Annotated[float, at.Ge(0), at.Lt(100)]
        an_int: Annotated[int, at.Ge(0), at.Lt(100)]
        a_bool: bool
        a_string: Annotated[str, at.Regex(r"^foo$")]
        a_none: None

    validator = build_validator(MyModel)
    assert validator.validate_python({"a_float": 1, "an_int": 0, "a_bool": "True", "a_string": "foo", "a_none": None}) == MyModel(1.0, 0, True, "foo", None)


def test_any() -> None:
    @dataclass
    class MyModel:
        any_scalar: Any
        any_list: List[Any]

    validator = build_validator(MyModel)
    o = object()
    assert validator.validate_python({"any_scalar": o, "any_list": [o]}) == MyModel(o, [o])
    with pytest.raises(ValidationError):
        validator.validate_python({"any_scalar": o, "any_list": o})


def test_list() -> None:
    @dataclass
    class MyModel:
        a_list: Annotated[List[float], at.Len(1, 10)]

    validator = build_validator(MyModel)
    assert validator.validate_python({"a_list": [1]}) == MyModel(
        [1.0]
    )
    with pytest.raises(ValidationError):
        validator.validate_python({"a_list": list(range(20))})


def test_set() -> None:
    @dataclass
    class MyModel:
        a_set: Annotated[Set[float], at.Len(1, 10)]

    validator = build_validator(MyModel)
    assert validator.validate_python({"a_set": [1, 1, 1.1]}) == MyModel(
        {1.0, 1.1}
    )
    with pytest.raises(ValidationError):
        validator.validate_python({"a_set": list(range(20))})


def test_dict() -> None:
    @dataclass
    class MyModel:
        a_dict: Annotated[Dict[int, int], at.Len(1, 10)]

    validator = build_validator(MyModel)
    assert validator.validate_python({"a_dict": {1: 123}}) == MyModel(
        {1: 123}
    )
    with pytest.raises(ValidationError):
        validator.validate_python({"a_dict": {"not a num": 123}})
    with pytest.raises(ValidationError):
        validator.validate_python({"a_dict": {1: "not a num"}})
    with pytest.raises(ValidationError):
        validator.validate_python({"a_dict": {x: 123 for x in range(20)}})


def test_union() -> None:
    @dataclass
    class MyModel:
        a_union: Union[
            Annotated[int, at.Ge(0), at.Lt(100)], Annotated[float, at.Ge(100)]
        ]

    validator = build_validator(MyModel)
    assert validator.validate_python({"a_union": 101}) == MyModel(
        101.0
    )
    assert validator.validate_python({"a_union": 99}) == MyModel(
        99
    )


@dataclass
class RecursiveModel:
    inner: "Annotated[List[Optional[RecursiveModel]], at.Len(0, 1)]"


def test_recursive() -> None:
    validator = build_validator(RecursiveModel)
    assert validator.validate_python({"inner": []}) == RecursiveModel([])
    assert validator.validate_python({"inner": [{"inner": []}]}) == RecursiveModel(
        [RecursiveModel([])]
    )
    assert validator.validate_python({"inner": [{"inner": [None]}]}) == RecursiveModel(
        [RecursiveModel([None])]
    )
    assert validator.validate_python({"inner": [{"inner": [{"inner": []}]}]}) == RecursiveModel(
        [RecursiveModel([RecursiveModel([])])]
    )
    with pytest.raises(ValidationError):
        validator.validate_python({"inner": [{"inner": []}, {"inner": []}]})


def test_validation_failure() -> None:
    @dataclass
    class MyModel:
        foo: Annotated[str, at.Regex(r"^abc$")]

    validator = build_validator(MyModel)
    with pytest.raises(ValidationError):
        validator.validate_python({"foo": "abcd"})
