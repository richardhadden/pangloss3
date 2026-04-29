from pangloss_models import initialise
from pangloss_models.model_bases.conjunction import Conjunction
from pangloss_models.model_bases.document import Document
from pangloss_models.model_bases.entity import Entity
from pangloss_models.model_bases.reified_relation import (
    ReifiedRelation,
    ReifiedRelationDocument,
)
from pangloss_models.model_bases.semantic_space import SemanticSpace


def test_document_has_update_model():
    class Statement(Document):
        pass

    initialise()

    assert Statement.Update
    for field_name in {"id", "label", "type"}:
        assert field_name in Statement.Update.model_fields


def test_entity_has_update_model():
    class Person(Entity):
        pass

    initialise()

    assert Person.Update
    for field_name in {"id", "label", "type"}:
        assert field_name in Person.Update.model_fields


def test_conjunction_has_update_model():

    class Alternative[T](Conjunction):
        pass

    class Person(Entity):
        pass

    initialise()

    assert Alternative.Update

    assert Alternative[Person].Update


def test_reified_relation_has_update_model():

    class Identification[T](ReifiedRelation[T]):
        pass

    class Person(Entity):
        pass

    initialise()

    assert Identification.Update
    assert Identification[Person].Update


def test_reified_relation_document_has_update_model():
    class PersonInPlace[T](ReifiedRelationDocument[T]):
        pass

    class Person(Entity):
        pass

    initialise()

    assert PersonInPlace.Update

    assert PersonInPlace[Person].Update


def test_semantic_space_has_update_model():

    class Negative[T](SemanticSpace[T]):
        pass

    initialise()

    assert Negative.Update
