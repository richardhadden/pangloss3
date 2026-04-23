import warnings
from abc import ABC, abstractmethod
from functools import cache
from typing import TYPE_CHECKING, Any, ClassVar, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    PrivateAttr,
    create_model,
    model_validator,
)
from pydantic.alias_generators import to_camel

from pangloss_models.model_registry import ModelRegistry

if TYPE_CHECKING:
    from pangloss_models.field_definitions import (
        FieldBinding,
        FieldDefinition,
        ModelFieldDict,
        ModelFields,
    )
    from pangloss_models.model_bases.edge_model import EdgeModel


class _BaseObject(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True, alias_generator=to_camel, populate_by_name=True
    )

    _initialised: ClassVar[bool] = False


class DeclaredClassMeta(ABC):
    @property
    @abstractmethod
    def fields(self) -> ModelFieldDict[str, FieldDefinition]: ...

    field_definitions: ModelFields


class _DeclaredClass(_BaseObject):
    _meta: ClassVar[DeclaredClassMeta]
    _depends_on_classes: ClassVar[set[type[_DeclaredClass]]] = PrivateAttr()

    def __init_subclass__(cls):
        if (
            cls is not _DeclaredClass
            and cls
            not in {
                *_DeclaredClass.__subclasses__(),
            }
            and cls.__name__ not in {"Trait", "NonHeritableTrait"}
        ):
            print("REGISTERING", cls)
            ModelRegistry.register(cls)
        return super().__init_subclass__()

    @classmethod
    def __pydantic_init_subclass__(cls, **_):
        cls._depends_on_classes = set()

    @classmethod
    def __initialise__(cls):
        cls._initialised = True

    """
    @classmethod
    def __pydantic_on_complete__(cls) -> None:

        try:
            pass
            ModelRegistry.finalise()

        except Exception as e:
            print("Error finalising: error::", e.args, type(e))
            print(traceback.print_exc())
            pass

        return super().__pydantic_on_complete__()
    """

    @classmethod
    def initialise_meta(cls):
        pass


class MetaGetter[T: type[_ActionClass]]:
    """Descriptor class for getting the _meta class from
    the _DeclaredClass of an _ActionClass"""

    def __get__(self, instance, owner: T):
        return owner._owner._meta


class GetItemViaAttrDict[T](dict):
    def __getattr__(self, name) -> type[T]:
        if name in self:
            return self[name]
        return super().__getattribute__(name)


class _ActionClass(_BaseObject):
    _owner: ClassVar[type[_DeclaredClass]]
    _meta: ClassVar = MetaGetter[type[Self]]()
    _via: ClassVar[GetItemViaAttrDict[Self]]

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        cls._via = GetItemViaAttrDict()
        return super().__pydantic_init_subclass__(**kwargs)

    @classmethod
    @cache
    def apply_edge_model(cls, edge_model: type[EdgeModel]) -> type[Self]:
        """Creates a variant of the model with additional 'edge_property' field
        of the type supplied"""

        # For a ReifiedRelationDocument, we need to construct a better name for the class by
        # some introspection of the origin and args
        if origin := cls._owner.__pydantic_generic_metadata__["origin"]:
            base_model_name = (
                f"{origin.__name__}"
                f"[{', '.join(arg.__name__ for arg in cls._owner.__pydantic_generic_metadata__['args'])}]"
                f"{cls.__name__.split(']')[1]}"
            )

        else:
            base_model_name = cls.__name__

        model = create_model(
            f"{base_model_name}Via{edge_model.__name__}",
            __base__=cls,
            edge_properties=edge_model,
        )
        cls._via[edge_model.__name__] = model
        return model


class _ReferenceViewBase(_ActionClass):
    id: UUID
    label: str


class _ReferenceSetBase(_ActionClass):
    id: UUID

    @model_validator(mode="after")
    def remove_label(self):
        """Should not start setting the label of a ReferenceSet,
        but it's allowed as a field as it might be nice sometimes
        to write it in code for clarity"""
        self.label = None
        return self


def allow_bind_on_this_item(item: _CreateBase, binding: FieldBinding) -> bool:
    return bool(
        (
            binding.allowed_type_names
            and getattr(item, "type") in binding.allowed_type_names
        )
        or (
            binding.excluded_type_names
            and getattr(item, "type") not in binding.excluded_type_names
        )
        or (not binding.allowed_type_names and not binding.excluded_type_names)
    )


def recursively_add_bound_field_values(
    item: _CreateBase, binding: FieldBinding, value=None
):
    """Given an item, a FieldBinding instance and a value, try to
    bind values where rules are followed, and call itself to try on
    all nested items"""
    child_bound_fields = binding.child_fields
    if isinstance(item, _CreateBase) and allow_bind_on_this_item(item, binding):
        for child_bound_field in child_bound_fields:
            if isinstance(item, list):
                for ri in item:
                    if hasattr(ri, child_bound_field) and not getattr(
                        ri, child_bound_field, None
                    ):
                        setattr(ri, child_bound_field, value)
            else:
                if hasattr(item, child_bound_field) and not getattr(
                    item, child_bound_field, None
                ):
                    setattr(item, child_bound_field, value)
    for related_field_name in item._meta.fields.relation_fields.keys():
        child_item = getattr(item, related_field_name)
        if isinstance(child_item, list):
            for ci in child_item:
                recursively_add_bound_field_values(ci, binding, value)
        else:
            recursively_add_bound_field_values(child_item, binding, value)


class _CreateBase(_ActionClass):
    def _to_db_model(self):
        return self._owner.CreateDB(**self.model_dump())  # type: ignore

    @model_validator(mode="after")
    def propagate_bound_values(self) -> Self:
        """Get any binding-fields for this model and try to bind
        on nested objects"""
        for (
            field_name,
            bindings,
        ) in self._meta.fields.bind_to_child_field_bindings.items():
            for binding in bindings:
                value = getattr(self, binding.bound_field)
                if binding.converter:
                    value = binding.converter(value)
                related_item = getattr(self, field_name)
                recursively_add_bound_field_values(related_item, binding, value=value)

        return self


class _CreateDBBase(_ActionClass):
    def __init__(self, **kwargs):

        # Calling model_construct emits a warning that the data might not be valid,
        # so catch these and supress. This is fine as we later pass the data back to
        # the class.__init__, which will validate it
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if f := getattr(
                self._owner, "to_db_create", getattr(self._owner, "to_db", None)
            ):
                data = f(self.__class__.model_construct(**kwargs))
                if isinstance(data, dict):
                    super().__init__(**data)
                else:
                    super().__init__(**data.model_dump())
            else:
                super().__init__(**kwargs)


class _ViewBase(_ActionClass):
    id: UUID


class _UpdateBase(_ActionClass):
    id: UUID
