from typing import Annotated, get_args, get_origin, no_type_check
from uuid import UUID

from pangloss_models import initialise
from pangloss_models.model_bases.base_models import _APIHeadMeta
from pangloss_models.model_bases.document import Document
from pangloss_models.model_bases.entity import Entity
from pangloss_models.model_bases.reified_relation import ReifiedRelationDocument


@no_type_check
def test_document_has_head_view():
    class Person(Entity):
        pass

    class Statement(Document):
        name: str
        person: Person
        action: Action

    class Action(Document):
        pass

    initialise()

    assert Statement.HeadView

    assert "name" in Statement.HeadView.model_fields
    assert Statement.HeadView.model_fields["name"].annotation is str

    assert "label" in Statement.HeadView.model_fields
    assert Statement.HeadView.model_fields["label"].annotation is str

    assert "id" in Statement.HeadView.model_fields
    assert Statement.HeadView.model_fields["id"].annotation is UUID

    assert "meta" in Statement.HeadView.model_fields
    assert Statement.HeadView.model_fields["meta"].annotation is _APIHeadMeta

    assert "person" in Statement.HeadView.model_fields
    assert Statement.HeadView.model_fields["person"].annotation is Person.ReferenceView

    assert "action" in Statement.HeadView.model_fields
    assert Statement.HeadView.model_fields["action"].annotation is Action.View


@no_type_check
def test_entity_has_head_view():
    class Person(Entity):
        name: str

    initialise()

    assert Person.HeadView

    assert "name" in Person.HeadView.model_fields
    assert Person.HeadView.model_fields["name"].annotation is str

    assert "label" in Person.HeadView.model_fields
    assert Person.HeadView.model_fields["label"].annotation is str

    assert "id" in Person.HeadView.model_fields
    assert Person.HeadView.model_fields["id"].annotation is UUID

    assert "meta" in Person.HeadView.model_fields
    assert Person.HeadView.model_fields["meta"].annotation is _APIHeadMeta


@no_type_check
def test_reified_relation_document_has_head_view():
    class Person(Entity):
        pass

    class Place(Entity):
        pass

    class SomethingInPlace[T](ReifiedRelationDocument[T]):
        place: Place

    class Statement(Document):
        person_in_place: SomethingInPlace[Person]

    initialise()

    assert SomethingInPlace[Person].HeadView

    assert "place" in SomethingInPlace[Person].HeadView.model_fields
    assert (
        SomethingInPlace[Person].HeadView.model_fields["place"].annotation
        is Place.ReferenceView
    )
    assert "target" in SomethingInPlace[Person].HeadView.model_fields
    target_annotation = (
        SomethingInPlace[Person].HeadView.model_fields["target"].annotation
    )
    assert get_origin(target_annotation) is list
    annotated = get_args(target_annotation)[0]

    assert get_origin(annotated) is Annotated

    assert get_args(annotated)[0] is Person.ReferenceView

    assert (
        SomethingInPlace[Person].HeadView.model_fields["meta"].annotation
        is _APIHeadMeta
    )

    assert SomethingInPlace[Person].HeadView._owner is SomethingInPlace[Person]
