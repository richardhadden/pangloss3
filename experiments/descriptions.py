from typing import Annotated

from pydantic import BaseModel


class Thing(BaseModel):
    stuff: Annotated[str, "Here is a string"]
    otherstuff: str


print(Thing.model_fields["otherstuff"])
