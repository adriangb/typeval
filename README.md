# typeval

A prototype for integrating annotated-types with pydantic-core.

This is purely for exploration, it is highly likely that this will not be maintained long term.

## Example

```python
from dataclasses import dataclass
from typing import Annotated

from annotated_types import Gt, Len
from typeval import Validator

Name = Annotated[str, Len(0)]
Age = Annotated[int, Gt(0)]

Students = dict[Name, Age]

@dataclass
class Classroom:
    teacher: Name
    students: Students

classroom = Validator(Classroom).validate_python(
    {
        "teacher": "Foo Bar",
        "students": {
            "Fizz": 3,
            "Buzz": 5,
        }
    }
)

students = Validator(Students).validate_python(
    {
        "Fizz": 3,
        "Buzz": 5,
    }
)
```
