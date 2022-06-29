from typing import Any, Generic, Type, TypeVar

from typeval._builder import build_validator

T = TypeVar("T")


class Validator(Generic[T]):
    __slots__ = ("_validator",)

    def __init__(self, model: Type[T]) -> None:
        self._validator = build_validator(model)

    def validate_python(self, input: Any) -> T:
        return self._validator.validate_python(input)

    def validate_json(self, input: str) -> T:
        return self._validator.validate_json(input)
