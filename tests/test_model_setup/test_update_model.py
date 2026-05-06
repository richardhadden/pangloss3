import datetime
from inspect import isclass
from types import UnionType
from typing import Annotated, Literal, get_args, get_origin, no_type_check
from uuid import UUID, uuid7

import pytest
from annotated_types import Gt, MinLen
from pydantic import AnyHttpUrl, ValidationError

from pangloss_models import initialise
from pangloss_models.exceptions import PanglossMetaError
from pangloss_models.field_definitions import (
    FieldBinding,
    FieldSubclassing,
    ListFieldDefinition,
    LiteralFieldDefinition,
    RelationFieldDefinition,
)
from pangloss_models.model_bases.annotated_value import AnnotatedValue
from pangloss_models.model_bases.configs import RelationConfig
from pangloss_models.model_bases.conjunction import Conjunction, _ConjunctionCreateBase
from pangloss_models.model_bases.document import Document
from pangloss_models.model_bases.edge_model import EdgeModel
from pangloss_models.model_bases.embedded import Embedded
from pangloss_models.model_bases.entity import Entity
from pangloss_models.model_bases.helpers import DBField, Fulfils, ViaEdge
from pangloss_models.model_bases.reified_relation import (
    ReifiedRelation,
    ReifiedRelationDocument,
    _ReifiedRelationCreateBase,
    _ReifiedRelationUpdateBase,
)
from pangloss_models.model_bases.semantic_space import (
    SemanticSpace,
    _SemanticSpaceCreateBase,
)
from pangloss_models.model_bases.trait import Trait


def test_document_has_update_model():
    class Statement(Document):
        pass

    initialise()

    assert Statement.Update
    for field_name in {"id", "label", "type"}:
        assert field_name in Statement.Update.model_fields

    assert Statement.Update.model_fields["type"].annotation == Literal["Statement"]


def test_entity_has_update_model():
    class Person(Entity):
        pass

    initialise()

    assert Person.Update
    for field_name in {"id", "label", "type"}:
        assert field_name in Person.Update.model_fields

    assert Person.Update.model_fields["type"].annotation == Literal["Person"]


def test_conjunction_has_update_model():

    class Alternative[T](Conjunction):
        pass

    class Person(Entity):
        pass

    initialise()

    assert Alternative.Update

    assert Alternative[Person].Update

    for field_name in {"id", "type"}:
        assert field_name in Alternative.Update.model_fields

    assert Alternative.Update.model_fields["type"].annotation == Literal["Alternative"]
    assert (
        Alternative[Person].Update.model_fields["type"].annotation
        == Literal["Alternative"]
    )


def test_reified_relation_has_update_model():

    class Identification[T](ReifiedRelation[T]):
        pass

    class Person(Entity):
        pass

    initialise()

    assert Identification.Update
    assert Identification[Person].Update

    for field_name in {"id", "type"}:
        assert field_name in Identification.Update.model_fields
        assert field_name in Identification[Person].Update.model_fields

    assert (
        Identification.Update.model_fields["type"].annotation
        == Literal["Identification"]
    )

    assert (
        Identification[Person].Update.model_fields["type"].annotation
        == Literal["Identification"]
    )


def test_reified_relation_document_has_update_model():
    class PersonInPlace[T](ReifiedRelationDocument[T]):
        pass

    class Person(Entity):
        pass

    initialise()

    assert PersonInPlace.Update

    assert PersonInPlace[Person].Update

    for field_name in {"id", "type"}:
        assert field_name in PersonInPlace.Update.model_fields
        assert field_name in PersonInPlace[Person].Update.model_fields

    assert (
        PersonInPlace.Update.model_fields["type"].annotation == Literal["PersonInPlace"]
    )
    assert (
        PersonInPlace[Person].Update.model_fields["type"].annotation
        == Literal["PersonInPlace"]
    )


def test_semantic_space_has_update_model():

    class Negative[T](SemanticSpace[T]):
        pass

    class Action(Document):
        pass

    initialise()

    assert Negative.Update
    assert Negative[Action].Update

    for field_name in {"id", "type"}:
        assert field_name in Negative.Update.model_fields
        assert field_name in Negative[Action].Update.model_fields

    assert Negative.Update.model_fields["type"].annotation == Literal["Negative"]
    assert (
        Negative[Action].Update.model_fields["type"].annotation == Literal["Negative"]
    )


def test_literal_field_on_update_model():
    class Statement(Document):
        number: int

    class Dude(Entity):
        name: str

    initialise()

    assert Statement.Update.model_fields["number"]
    assert Statement.Update.model_fields["number"].annotation is int

    assert Dude.Update.model_fields["name"]
    assert Dude.Update.model_fields["name"].annotation is str


@no_type_check
def test_relation_to_embedded():
    class Date(Embedded):
        when: datetime.datetime

    class Other(Date):
        when: datetime.datetime

    class Statement(Document):
        date: Date

    initialise()

    assert Date.Update.model_fields["when"].annotation is datetime.datetime
    assert Date.Update.model_fields["type"].annotation == Literal["Date"]

    assert Statement._meta.fields["date"]

    assert Statement.Create.model_fields["date"]
    assert (
        Statement.Create.model_fields["date"].annotation == Date.Create | Other.Create
    )

    st_update = Statement.Update(
        id=uuid7(), label="A Statement", date={"type": "Date", "when": "2019-01-01"}
    )

    assert isinstance(st_update.date, Date.Create)

    st_update2 = Statement.Update(
        id=uuid7(),
        label="A Statement",
        date={"id": uuid7(), "type": "Date", "when": "2019-01-01"},
    )

    assert isinstance(st_update2.date, Date.Update)

    st_update3 = Statement.Update(
        id=uuid7(),
        label="A Statement",
        date={"id": uuid7(), "type": "Other", "when": "2019-01-01"},
    )

    assert isinstance(st_update3.date, Other.Update)


@no_type_check
def test_camel_case():
    class Statement(Document):
        some_snake: str

    initialise()

    st = Statement.Update(**dict(id=uuid7(), label="A statement", someSnake="hello"))
    assert st.some_snake == "hello"


@no_type_check
def test_meta_accessible_through_update():
    class Statement(Document):
        some_snake: str

    initialise()

    assert Statement.Update._meta is Statement._meta


@no_type_check
def test_type_field_is_correct():
    class Statement(Document):
        pass

    initialise()

    assert Statement.Update.model_fields["type"].annotation == Literal["Statement"]


@no_type_check
def test_update_model_for_document_with_no_id():
    class Statement(Document):
        pass

    initialise()

    assert Statement.Update

    assert Statement.Update._owner is Statement

    assert "id" in Statement.Update.model_fields

    uuid_value = uuid7()

    st = Statement.Update(id=uuid_value, label="A Statement")
    assert st.label == "A Statement"
    assert st.id == uuid_value


@no_type_check
def test_add_fields_to_document_update_model():
    class Statement(Document):
        name: str
        age: int
        numbers: list[int]

    initialise()

    assert "name" in Statement.Update.model_fields
    name_field = Statement.Update.model_fields["name"]
    assert name_field.annotation is str

    assert "age" in Statement.Update.model_fields
    age_field = Statement.Update.model_fields["age"]
    assert age_field.annotation is int

    assert "numbers" in Statement.Update.model_fields
    numbers_field = Statement.Update.model_fields["numbers"]
    assert numbers_field.annotation == list[int]

    st = Statement.Update(
        id=uuid7(), label="A Statement", name="John", age=12, numbers=[1, 2, 3]
    )
    assert st.label == "A Statement"
    assert st.name == "John"
    assert st.age == 12
    assert st.numbers == [1, 2, 3]

    with pytest.raises(ValidationError):
        st = Statement.Update(
            id=uuid7(), label="A Statement", name="John", age=12, numbers="WRONG"
        )


@no_type_check
def test_add_simple_relation_from_document_to_entity():

    class Statement(Document):
        was_carried_out_by: Person

    class Person(Entity):
        pass

    initialise()

    assert Statement.Update
    assert Statement.Update.model_fields["was_carried_out_by"]
    assert (
        Statement.Update.model_fields["was_carried_out_by"].annotation
        is Person.ReferenceSet
    )


@no_type_check
def test_add_simple_relation_from_document_to_entity_inheriting():

    class Statement(Document):
        was_carried_out_by: Person

    class Person(Entity):
        pass

    class Dude(Person):
        pass

    initialise()

    assert Statement.Update
    assert Statement.Update.model_fields["was_carried_out_by"]
    assert (
        Statement.Update.model_fields["was_carried_out_by"].annotation
        == Person.ReferenceSet | Dude.ReferenceSet
    )


@no_type_check
def test_add_simple_relation_from_document_to_by_union():

    class Statement(Document):
        was_carried_out_by: Person | Dude

    class Person(Entity):
        pass

    class Dude(Entity):
        pass

    initialise()

    assert Statement.Update
    assert Statement.Update.model_fields["was_carried_out_by"]
    assert (
        Statement.Update.model_fields["was_carried_out_by"].annotation
        == Person.ReferenceSet | Dude.ReferenceSet
    )

    st = Statement.Create(
        label="A Statement", was_carried_out_by={"type": "Dude", "id": uuid7()}
    )
    assert st.label == "A Statement"
    assert isinstance(st.was_carried_out_by, Dude.ReferenceSet)


@no_type_check
def test_add_simple_relation_from_document_to_entity_with_list_wrapper():
    class Statement(Document):
        was_carried_out_by: list[Person]

    class Person(Entity):
        pass

    initialise()

    assert Statement.Update
    assert Statement.Update.model_fields["was_carried_out_by"]
    annotation = Statement.Update.model_fields["was_carried_out_by"].annotation
    assert get_args(get_args(annotation)[0])[0] is Person.ReferenceSet

    st = Statement.Update(
        id=uuid7(),
        label="A Statement",
        was_carried_out_by=[{"type": "Person", "id": uuid7()}],
    )

    assert isinstance(st.was_carried_out_by, list)
    assert isinstance(st.was_carried_out_by[0], Person.ReferenceSet)


@no_type_check
def test_add_simple_relation_from_document_to_entity_via_edge():

    class Statement(Document):
        was_carried_out_by: ViaEdge[Person, Certainty]

    class Person(Entity):
        pass

    class Certainty(EdgeModel):
        pass

    initialise()

    assert Statement.Update
    assert Statement.Update.model_fields["was_carried_out_by"]
    assert (
        Statement.Update.model_fields["was_carried_out_by"].annotation
        is Person.ReferenceSet._via.Certainty
    )

    assert set(Person.ReferenceSet._via.Certainty.model_fields.keys()) == {
        "edge_properties",
        "id",
        "label",
        "type",
    }


@no_type_check
def test_add_relation_from_document_to_document():
    class Statement(Document):
        action: Action

    class Action(Document):
        pass

    initialise()

    assert "action" in Statement._meta.fields
    assert Statement.Update.model_fields["action"]
    assert (
        Statement.Update.model_fields["action"].annotation
        == Action.Create | Action.Update
    )


@no_type_check
def test_add_relation_from_document_to_document_via_edge():
    class Statement(Document):
        action: ViaEdge[Action, Certainty]

    class Action(Document):
        pass

    class Certainty(EdgeModel):
        pass

    initialise()

    assert "action" in Statement._meta.fields
    assert Statement.Update.model_fields["action"]
    assert (
        Statement.Update.model_fields["action"].annotation
        == Action.Create._via.Certainty | Action.Update._via.Certainty
    )


@no_type_check
def test_add_self_reference_to_document():
    class DeferredOrder(Document):
        deferred_order: Order

    class Task(Document):
        pass

    class Order(Document):
        thing_ordered: Order | DeferredOrder | Task

    class SubTask(Task):
        pass

    initialise()

    assert (
        Order.Update.model_fields["thing_ordered"].annotation
        == Order.Create
        | DeferredOrder.Create
        | Task.Create
        | SubTask.Create
        | Order.Update
        | DeferredOrder.Update
        | Task.Update
        | SubTask.Update
    )


"""Testing up to here"""


@no_type_check
def test_relation_to_entity_via_reified_relation():
    class Identification[TTarget](ReifiedRelation[TTarget]):
        some_value: int

    class Statement(Document):
        is_about_person: Identification[Person]

    class Person(Entity):
        pass

    initialise()

    assert issubclass(Identification.Update, _ReifiedRelationUpdateBase)
    assert Identification.Update.model_fields["some_value"].annotation is int

    """
    assert (
        Statement.Update.model_fields["is_about_person"].annotation.__name__
        == "Identification[Person]Create"
    )

    identification_person_create_model = Statement.Create.model_fields[
        "is_about_person"
    ].annotation
    assert issubclass(identification_person_create_model, Identification.Create)
    assert (
        identification_person_create_model.model_fields["some_value"].annotation is int
    )
    assert identification_person_create_model._owner is Identification

    target_annotation = identification_person_create_model.model_fields[
        "target"
    ].annotation
    assert get_origin(target_annotation) is list
    assert get_args(get_args(target_annotation)[0])[0] is Person.ReferenceSet

    st_uuid = uuid7()

    st = Statement.Create(
        label="A Statement",
        is_about_person={
            "type": "Identification",
            "target": [{"type": "Person", "id": st_uuid}],
            "some_value": 1,
        },
    )

    assert isinstance(st.is_about_person, identification_person_create_model)
    assert st.is_about_person.target[0].id == st_uuid
    """


@no_type_check
def test_relation_with_double_reified_relation():
    class WithProxy[TTarget, TProxy](ReifiedRelation[TTarget]):
        proxy: list[TProxy]

    class Identification[T](ReifiedRelation[T]):
        some_value: int

    class Statement(Document):
        is_about_person: WithProxy[Identification[Person], Identification[Person]]

    class Person(Entity):
        pass

    initialise()

    is_about_person_field = Statement.Create.model_fields["is_about_person"]
    assert (
        is_about_person_field.annotation.__name__
        == "WithProxy[Identification[Person], Identification[Person]]Create"
    )
    assert issubclass(is_about_person_field.annotation, WithProxy.Create)
    assert is_about_person_field.annotation.model_fields["target"].annotation
    proxy_target_annotation = is_about_person_field.annotation.model_fields[
        "target"
    ].annotation
    assert get_origin(proxy_target_annotation) is list
    assert get_origin(get_args(proxy_target_annotation)[0]) is Annotated

    proxy_identification_target_annotation = get_args(
        get_args(proxy_target_annotation)[0]
    )[0]
    assert issubclass(proxy_identification_target_annotation, Identification.Create)
    assert (
        get_origin(
            proxy_identification_target_annotation.model_fields["target"].annotation
        )
        is list
    )
    assert (
        get_origin(
            get_args(
                proxy_identification_target_annotation.model_fields["target"].annotation
            )[0]
        )
        is Annotated
    )
    assert (
        get_args(
            get_args(
                proxy_identification_target_annotation.model_fields["target"].annotation
            )[0]
        )[0]
        is Person.ReferenceSet
    )

    assert is_about_person_field.annotation.model_fields["proxy"].annotation
    proxy_proxy_annotation = is_about_person_field.annotation.model_fields[
        "proxy"
    ].annotation
    assert get_origin(proxy_proxy_annotation) is list
    assert get_origin(get_args(proxy_proxy_annotation)[0]) is Annotated

    proxy_identification_target_annotation = get_args(
        get_args(proxy_proxy_annotation)[0]
    )[0]
    assert issubclass(proxy_identification_target_annotation, Identification.Create)
    assert (
        get_origin(
            proxy_identification_target_annotation.model_fields["target"].annotation
        )
        is list
    )
    assert (
        get_origin(
            get_args(
                proxy_identification_target_annotation.model_fields["target"].annotation
            )[0]
        )
        is Annotated
    )
    assert (
        get_args(
            get_args(
                proxy_identification_target_annotation.model_fields["target"].annotation
            )[0]
        )[0]
        is Person.ReferenceSet
    )


@no_type_check
def test_relation_with_semantic_space():
    class Negative[T](SemanticSpace[T]):
        pass

    class Factoid(Document):
        has_statement: list[Statement | Negative[Statement]]

    class Statement(Document):
        text: str

    initialise()

    statement_field = Factoid.Create.model_fields["has_statement"]
    assert statement_field
    assert get_origin(statement_field.annotation) is list
    assert get_origin(get_args(statement_field.annotation)[0]) is Annotated
    # Having peeled away the list and the Annotated...
    type_union = get_args(get_args(statement_field.annotation)[0])[0]
    assert isinstance(type_union, UnionType)
    type_union_items = get_args(type_union)
    assert set(t.__name__ for t in type_union_items) == set(
        ["StatementCreate", "Negative[Statement]Create"]
    )

    Negative_Statement_Create: type[_SemanticSpaceCreateBase] = [
        c for c in type_union_items if c.__name__ == "Negative[Statement]Create"
    ][0]

    assert issubclass(Negative_Statement_Create, _SemanticSpaceCreateBase)

    f = Factoid(
        label="A Factoid",
        has_statement=[
            {
                "type": "Negative",
                "contents": [
                    {
                        "type": "Statement",
                        "label": "Yohoo!",
                        "text": "Woo",
                    }
                ],
            }
        ],
    )

    assert f.label == "A Factoid"
    assert f.has_statement[0].type == "Negative"
    assert isinstance(f.has_statement[0], Negative.Create)
    assert f.has_statement[0].contents[0].type == "Statement"
    assert isinstance(f.has_statement[0].contents[0], Statement.Create)


@no_type_check
def test_relation_with_conjunction():
    class Causes[TCause, TResult](Conjunction):
        cause: TCause
        result: TResult

    class Statement(Document):
        pass

    class Factoid(Document):
        has_statements: Statement | Causes[Statement, Statement]

    initialise()

    # Check that Factoid.Create has the has_statements field
    assert "has_statements" in Factoid.Create.model_fields

    # Check the annotation is a Union
    has_statements_field = Factoid.Create.model_fields["has_statements"]
    assert has_statements_field
    annotation = has_statements_field.annotation

    assert isinstance(annotation, UnionType)
    union_items = get_args(annotation)
    assert len(union_items) == 2
    assert set(t.__name__ for t in union_items) == {
        "StatementCreate",
        "Causes[Statement, Statement]Create",
    }

    # Check that Causes has a Create model
    assert hasattr(Causes, "Create")
    assert issubclass(Causes.Create, _ConjunctionCreateBase)
    print(union_items)
    # Check that the specialized Causes[Statement, Statement] has a Create model

    causes_statement_create = [
        item
        for item in union_items
        if item.__name__ == "Causes[Statement, Statement]Create"
    ][0]  # The Causes[Statement, Statement]Create
    assert issubclass(causes_statement_create, Causes.Create)
    assert "cause" in causes_statement_create.model_fields
    assert "result" in causes_statement_create.model_fields
    assert causes_statement_create.model_fields["cause"].annotation == Statement.Create
    assert causes_statement_create.model_fields["result"].annotation == Statement.Create

    # Create an instance with a Statement
    f1 = Factoid.Create(
        label="A Factoid",
        has_statements={
            "type": "Statement",
            "label": "A Statement",
        },
    )
    assert f1.label == "A Factoid"
    assert f1.has_statements.type == "Statement"
    assert isinstance(f1.has_statements, Statement.Create)

    # Create an instance with a Causes conjunction
    f2 = Factoid.Create(
        label="Another Factoid",
        has_statements={
            "type": "Causes",
            "cause": {
                "type": "Statement",
                "label": "Cause Statement",
            },
            "result": {
                "type": "Statement",
                "label": "Result Statement",
            },
        },
    )
    assert f2.label == "Another Factoid"
    assert f2.has_statements.type == "Causes"
    assert isinstance(f2.has_statements, causes_statement_create)
    assert f2.has_statements.cause.type == "Statement"
    assert isinstance(f2.has_statements.cause, Statement.Create)
    assert f2.has_statements.result.type == "Statement"
    assert isinstance(f2.has_statements.result, Statement.Create)


@no_type_check
def test_relation_to_trait():
    class Agent(Trait):
        pass

    class Person(Entity, Agent):
        pass

    class Group(Entity, Agent):
        pass

    class Posse(Group):
        pass

    class Organisation(Entity, Agent):
        pass

    class Statement(Document):
        thing_carried_out_by: Agent

    initialise()

    thing_carried_out_by_field = Statement.Create.model_fields["thing_carried_out_by"]
    assert (
        thing_carried_out_by_field.annotation
        == Person.ReferenceSet
        | Group.ReferenceSet
        | Organisation.ReferenceSet
        | Posse.ReferenceSet
    )

    st = Statement(
        label="A Statement", thing_carried_out_by={"type": "Group", "id": uuid7()}
    )


@no_type_check
def test_annotated_value():
    class WithCertainty[T](AnnotatedValue[T]):
        certainty: int

    class Naming(Document):
        name: WithCertainty[str]

    initialise()

    assert WithCertainty[str].model_fields["value"].annotation is str

    assert Naming.Create.model_fields["name"].annotation == WithCertainty[str]


@no_type_check
def test_db_field_not_in_create_model():

    class Statement(Document):
        some_field: int
        db_int_field: Annotated[int, DBField]
        person_field: Person
        db_person_field: Annotated[Person, DBField]
        embedded_field: Date
        db_embedded_field: Annotated[Date, DBField]

    class Person(Entity):
        pass

    class Date(Embedded):
        pass

    initialise()

    assert "some_field" in Statement.Create.model_fields
    assert "db_int_field" not in Statement.Create.model_fields
    assert "person_field" in Statement.Create.model_fields
    assert "db_person_field" not in Statement.Create.model_fields
    assert "embedded_field" in Statement.Create.model_fields
    assert "db_embedded_field" not in Statement.Create.model_fields


@no_type_check
def test_inherited_from_fulfils_is_optional():
    class PersonInPlace(Document):
        located_person: Person
        place: Place

    class Activity(Document, Fulfils[PersonInPlace]):
        person_responsible: Annotated[
            Person,
            RelationConfig(
                subclasses_parent_fields=[
                    FieldSubclassing("located_person", field_on_model=PersonInPlace)
                ]
            ),
        ]

    class Person(Entity):
        pass

    class Place(Entity):
        pass

    initialise()

    assert (
        Activity.Create.model_fields["person_responsible"].annotation
        is Person.ReferenceSet
    )

    assert Activity.Create.model_fields["place"].annotation == Place.ReferenceSet | None


def test_create_model_with_field_binding():
    class Action(Document):
        action_when: datetime.date
        action_when_optional: datetime.date | None

    class Statement(Document):
        when: datetime.date
        action: Annotated[
            Action,
            RelationConfig(
                bind_to_child_field=[
                    FieldBinding(
                        bound_field="when",
                        child_fields=["action_when", "action_when_optional"],
                        allowed_type_names=["Action"],
                    )
                ]
            ),
        ]

    initialise()

    action_model = Statement.Create.model_fields["action"].annotation
    assert isclass(action_model) and issubclass(action_model, Action.Create)
    assert action_model.model_fields["action_when"].annotation == datetime.date | None
    assert (
        action_model.model_fields["action_when_optional"].annotation
        == datetime.date | None
    )


@no_type_check
def test_create_model_with_field_binding_through_intermediate():

    class Action(Document):
        action_when: datetime.date

    class Negative[T](SemanticSpace[T]):
        pass

    class Statement(Document):
        when: datetime.date
        action: Annotated[
            Negative[Action],
            RelationConfig(
                bind_to_child_field=[
                    FieldBinding(
                        bound_field="when",
                        child_fields=["action_when"],
                        allowed_type_names=["Action"],
                    )
                ]
            ),
        ]

    initialise()

    negative_model = Statement.Create.model_fields["action"].annotation
    assert isclass(negative_model) and issubclass(negative_model, Negative.Create)

    negative_contents_fields = negative_model.model_fields["contents"]
    assert get_origin(negative_contents_fields.annotation) is list
    annotated_action_model = get_args(negative_contents_fields.annotation)[0]

    assert get_origin(annotated_action_model) is Annotated
    action_model = get_args(annotated_action_model)[0]
    assert action_model
    assert isclass(action_model) and issubclass(action_model, Action.Create)

    assert action_model.model_fields["action_when"].annotation == datetime.date | None

    st = Statement.Create(
        label="A Statement",
        when=datetime.date.today(),
        action={
            "type": "Negative",
            "contents": [
                {
                    "type": "Action",
                    "label": "An action",
                }
            ],
        },
    )

    assert st.action.contents[0].action_when == datetime.date.today()


@no_type_check
def test_create_model_with_field_binding_through_intermediate_with_transform():

    class Action(Document):
        action_when: datetime.date

    class Negative[T](SemanticSpace[T]):
        pass

    class Statement(Document):
        when: datetime.date
        action: Annotated[
            Negative[Action],
            RelationConfig(
                bind_to_child_field=[
                    FieldBinding(
                        bound_field="when",
                        child_fields=["action_when"],
                        allowed_type_names=["Action"],
                        converter=lambda x: x + datetime.timedelta(days=1),
                    )
                ]
            ),
        ]

    initialise()

    negative_model = Statement.Create.model_fields["action"].annotation
    assert isclass(negative_model) and issubclass(negative_model, Negative.Create)

    negative_contents_fields = negative_model.model_fields["contents"]
    assert get_origin(negative_contents_fields.annotation) is list
    annotated_action_model = get_args(negative_contents_fields.annotation)[0]

    assert get_origin(annotated_action_model) is Annotated
    action_model = get_args(annotated_action_model)[0]
    assert action_model
    assert isclass(action_model) and issubclass(action_model, Action.Create)

    assert action_model.model_fields["action_when"].annotation == datetime.date | None

    st = Statement.Create(
        label="A Statement",
        when=datetime.date.today(),
        action={
            "type": "Negative",
            "contents": [
                {
                    "type": "Action",
                    "label": "An action",
                }
            ],
        },
    )

    assert st.action.contents[
        0
    ].action_when == datetime.date.today() + datetime.timedelta(days=1)

    # Check we can convert to DB model, which will be proof of pudding
    st._to_db_model()


@no_type_check
def test_create_model_with_field_binding_through_intermediate_ignoring_type():

    class Action(Document):
        action_when: datetime.date
        subaction: SubAction

    class SubAction(Document):
        action_when: datetime.date

    class Negative[T](SemanticSpace[T]):
        pass

    class Statement(Document):
        when: datetime.date
        action: Annotated[
            Negative[Action],
            RelationConfig(
                bind_to_child_field=[
                    FieldBinding(
                        bound_field="when",
                        child_fields=["action_when"],
                        allowed_type_names=["SubAction"],
                        converter=lambda x: x + datetime.timedelta(days=1),
                    ),
                ]
            ),
        ]

    initialise()

    negative_model = Statement.Create.model_fields["action"].annotation
    assert isclass(negative_model) and issubclass(negative_model, Negative.Create)

    negative_contents_fields = negative_model.model_fields["contents"]
    assert get_origin(negative_contents_fields.annotation) is list
    annotated_action_model = get_args(negative_contents_fields.annotation)[0]

    assert get_origin(annotated_action_model) is Annotated
    action_model = get_args(annotated_action_model)[0]
    assert action_model
    assert isclass(action_model) and issubclass(action_model, Action.Create)

    assert action_model.model_fields["action_when"].annotation == datetime.date

    # Test that not providing Action.action_when raises error as binding only
    # applied to SubAction
    with pytest.raises(ValidationError):
        Statement.Create(
            label="A Statement",
            when=datetime.date.today(),
            action={
                "type": "Negative",
                "contents": [
                    {
                        "type": "Action",
                        "label": "An action",
                    }
                ],
            },
        )

    st = Statement.Create(
        label="A Statement",
        when=datetime.date.today(),
        action={
            "type": "Negative",
            "contents": [
                {
                    "type": "Action",
                    "label": "An action",
                    "action_when": datetime.date.today(),
                    "subaction": {
                        "type": "SubAction",
                        "label": "A SubAction",
                    },
                }
            ],
        },
    )

    assert st.action.contents[0].action_when == datetime.date.today()

    assert st.action.contents[
        0
    ].subaction.action_when == datetime.date.today() + datetime.timedelta(days=1)


@no_type_check
def test_create_model_with_field_binding_through_intermediate_ignoring_type_does_not_override_given_value():

    class Action(Document):
        action_when: datetime.date
        subaction: SubAction

    class SubAction(Document):
        action_when: datetime.date

    class Negative[T](SemanticSpace[T]):
        pass

    class Statement(Document):
        when: datetime.date
        action: Annotated[
            Negative[Action],
            RelationConfig(
                bind_to_child_field=[
                    FieldBinding(
                        bound_field="when",
                        child_fields=["action_when"],
                        allowed_type_names=["Action", "SubAction"],
                        converter=lambda x: x + datetime.timedelta(days=1),
                    ),
                ]
            ),
        ]

    initialise()

    negative_model = Statement.Create.model_fields["action"].annotation
    assert isclass(negative_model) and issubclass(negative_model, Negative.Create)

    negative_contents_fields = negative_model.model_fields["contents"]
    assert get_origin(negative_contents_fields.annotation) is list
    annotated_action_model = get_args(negative_contents_fields.annotation)[0]

    assert get_origin(annotated_action_model) is Annotated
    action_model = get_args(annotated_action_model)[0]
    assert action_model
    assert isclass(action_model) and issubclass(action_model, Action.Create)

    assert action_model.model_fields["action_when"].annotation == datetime.date | None

    st = Statement.Create(
        label="A Statement",
        when=datetime.date.today(),
        action={
            "type": "Negative",
            "contents": [
                {
                    "type": "Action",
                    "label": "An action",
                    "action_when": datetime.date.today(),
                    "subaction": {
                        "type": "SubAction",
                        "label": "A SubAction",
                    },
                }
            ],
        },
    )

    assert st.action.contents[0].action_when == datetime.date.today()

    assert st.action.contents[
        0
    ].subaction.action_when == datetime.date.today() + datetime.timedelta(days=1)


@no_type_check
def test_relation_validator():
    class Factoid(Document):
        statements: Annotated[
            list[Action],
            MinLen(1),
        ]

    class Action(Document):
        pass

    initialise()

    statements_field = Factoid._meta.fields["statements"]
    assert isinstance(statements_field, RelationFieldDefinition)

    assert statements_field.validators == [MinLen(1)]

    assert Factoid.Create.model_fields["statements"]
    assert Factoid.Create.model_fields["statements"].metadata == [MinLen(1)]

    with pytest.raises(ValidationError):
        Factoid.Create(label="A Factoid", statements=[])


@no_type_check
def test_literal_validators():
    class Factoid(Document):
        number: Annotated[
            int,
            Gt(1),
        ]

    initialise()

    statements_field = Factoid._meta.fields["number"]
    assert isinstance(statements_field, LiteralFieldDefinition)

    assert statements_field.validators == [Gt(1)]

    assert Factoid.Create.model_fields["number"]
    assert Factoid.Create.model_fields["number"].metadata == [Gt(1)]

    with pytest.raises(ValidationError):
        Factoid.Create(label="A Factoid", number=1)


@no_type_check
def test_list_validators():
    class Factoid(Document):
        numbers: Annotated[list[Annotated[int, Gt(1)]], MinLen(1)]

    initialise()

    statements_field = Factoid._meta.fields["numbers"]
    assert isinstance(statements_field, ListFieldDefinition)

    assert statements_field.validators == [MinLen(1)]
    assert statements_field.inner_type_validators == [Gt(1)]

    assert Factoid.Create.model_fields["numbers"]
    assert Factoid.Create.model_fields["numbers"].metadata == [MinLen(1)]

    with pytest.raises(ValidationError):
        Factoid.Create(label="A Factoid", numbers=[])

    with pytest.raises(ValidationError):
        Factoid.Create(label="A Factoid", numbers=[1])

    Factoid.Create(label="A Factoid", numbers=[2, 2, 2])
