from pangloss_models.model_bases.document import Document
from pangloss_models.model_bases.semantic_space import SemanticSpace
from pangloss_models.model_registry import ModelRegistry


def test_initialisation_of_single_model():

    class Factoid(Document):
        pass

    assert "Factoid" in ModelRegistry.all_models()


def test_initialisation_of_referenced_model():

    class Factoid(Document):
        statements: Statement

    class Statement(Document):
        title: str

    assert "Factoid" in ModelRegistry.all_models()
    assert "Statement" in ModelRegistry.all_models()

    print(ModelRegistry.all_models())

    assert Factoid._meta.fields["statements"]
    assert Statement._meta.fields["title"]

    assert Factoid.Create
    assert Factoid.Create.model_fields["statements"]

    assert Statement.Create
    assert Statement.Create.model_fields["title"]


def test_initialisation_of_referenced_model_reverse_order():

    class Statement(Document):
        title: str

    class Factoid(Document):
        statements: Statement

    assert "Factoid" in ModelRegistry.all_models()
    assert "Statement" in ModelRegistry.all_models()

    assert Factoid._meta.fields["statements"]
    assert Statement._meta.fields["title"]

    assert Factoid.Create
    assert Factoid.Create.model_fields["statements"]

    assert Statement.Create
    assert Statement.Create.model_fields["title"]


def test_initialisation_of_random_ordered_declaration_1():
    class Negative[T](SemanticSpace[T]):
        pass

    class Factoid(Document):
        statements: list[Negative[Order]]

    class Action(Document):
        pass

    class Order(Document):
        thing_ordered: Subjunctive[Action]

    class Subjunctive[T](SemanticSpace[T]):
        pass

    assert Factoid._meta.fields["statements"]

    assert Factoid.Create
    assert Order.Create
    assert Action.Create

    assert Factoid.Create.model_fields["statements"]
    assert Order.Create.model_fields["thing_ordered"]


def test_initialisation_interleaved_order():
    """Test with alternating document and generic declarations"""

    class Negative[T](SemanticSpace[T]):
        pass

    class Factoid(Document):
        statements: list[Negative[Order]]

    class Subjunctive[T](SemanticSpace[T]):
        pass

    class Order(Document):
        thing_ordered: Subjunctive[Action]

    class Action(Document):
        pass

    assert Factoid._meta.fields["statements"]

    assert Factoid.Create
    assert Order.Create
    assert Action.Create

    assert Factoid.Create.model_fields["statements"]
    assert Order.Create.model_fields["thing_ordered"]


def test_initialisation_action_first():
    """Test with Action defined before Order"""

    class Action(Document):
        pass

    class Subjunctive[T](SemanticSpace[T]):
        pass

    class Order(Document):
        thing_ordered: Subjunctive[Action]

    class Negative[T](SemanticSpace[T]):
        pass

    class Factoid(Document):
        statements: list[Negative[Order]]

    assert Factoid._meta.fields["statements"]
    assert Order._meta.fields["thing_ordered"]

    assert Factoid.Create
    assert Order.Create
    assert Action.Create
    assert Subjunctive[Action].Create
    assert Negative[Order].Create

    assert Factoid.CreateDB
    assert Order.CreateDB
    assert Action.CreateDB
    assert Subjunctive[Action].CreateDB
    assert Negative[Order].CreateDB

    assert Factoid.Create.model_fields["statements"]
    assert Order.Create.model_fields["thing_ordered"]

    assert Factoid.CreateDB.model_fields["statements"]
    assert Order.CreateDB.model_fields["thing_ordered"]
