from typing import Annotated, ClassVar

from pydantic import ConfigDict, Field
from pydantic_meta_kit import BaseMeta, InheritValue, MetaRules

from pangloss_models.field_definitions import (
    FieldDefinition,
    ModelFieldDict,
    ModelFields,
)
from pangloss_models.model_bases.base_models import (
    _CreateBase,
    _CreateDBBase,
    _DeclaredClass,
)


class SemanticSpaceMeta(BaseMeta):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    _owner_class: type[SemanticSpace] | InheritValue = InheritValue.AS_DEFAULT
    abstract: Annotated[bool, MetaRules.DO_NOT_INHERIT] = False
    require_label: bool | InheritValue = False
    field_definitions: ModelFields = Field(default_factory=ModelFields)

    @property
    def fields(self) -> ModelFieldDict[str, FieldDefinition]:
        return self.field_definitions.fields


class _SemanticSpaceCreateBase(_CreateBase):
    pass


class _SemanticSpaceCreateDBBase(_CreateDBBase):
    pass


class SemanticSpace[TContents](_DeclaredClass):
    _meta: ClassVar[SemanticSpaceMeta] = SemanticSpaceMeta()  # pyright: ignore[reportIncompatibleVariableOverride]

    Create: ClassVar[type[_SemanticSpaceCreateBase]]
    CreateDB: ClassVar[type[_SemanticSpaceCreateDBBase]]

    contents: list[TContents]

    @classmethod
    def __pydantic_init_subclass__(cls, **_):

        # Set model it uninitialised, as may inherit _initialised from parent class
        cls._initialised = False

        # Make sure _meta class is new and not inherited
        cls._meta = cls.__dict__.get("_meta", SemanticSpaceMeta())  # pyright: ignore[reportIncompatibleVariableOverride]

        # Set owner class on cls._meta
        cls._meta._owner_class = cls

        cls._register()
