from types import UnionType
from typing import Annotated, Any, ClassVar, Literal, Union

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag
from pydantic import create_model as pydantic_create_model
from pydantic.alias_generators import to_camel
from pydantic.fields import FieldInfo

from pangloss_models.field_definitions import EmbeddedFieldDefinition
from pangloss_models.model_bases.base_models import _DeclaredClass, _UpdateBase
from pangloss_models.model_bases.conjunction import Conjunction, _ConjunctionUpdateBase
from pangloss_models.model_bases.document import Document, _DocumentUpdateBase
from pangloss_models.model_bases.embedded import Embedded, _EmbeddedUpdateBase
from pangloss_models.model_bases.entity import Entity, _EntityUpdateBase
from pangloss_models.model_bases.reified_relation import (
    ReifiedRelation,
    ReifiedRelationDocument,
    _ReifiedRelationDocumentUpdateBase,
    _ReifiedRelationUpdateBase,
)
from pangloss_models.model_bases.semantic_space import (
    SemanticSpace,
    _SemanticSpaceUpdateBase,
)
from pangloss_models.utils import (
    field_has_inherited_field_bindings,
    map_validators_to_kwargs,
)


def can_have_update_model(model: type[_DeclaredClass]) -> bool:
    return issubclass(
        model,
        (
            Document,
            Entity,
            ReifiedRelation,
            ReifiedRelationDocument,
            Conjunction,
            SemanticSpace,
            Embedded,
        ),
    )


def get_update_base_model_type(
    model: type[
        Document
        | Embedded
        | Entity
        | ReifiedRelation
        | ReifiedRelationDocument
        | Conjunction
        | SemanticSpace
    ],
) -> type[_UpdateBase] | None:
    if issubclass(model, Document):
        return _DocumentUpdateBase
    elif issubclass(model, Entity):
        return _EntityUpdateBase
    elif issubclass(model, ReifiedRelation):
        return _ReifiedRelationUpdateBase
    elif issubclass(model, ReifiedRelationDocument):
        return _ReifiedRelationDocumentUpdateBase
    elif issubclass(model, Conjunction):
        return _ConjunctionUpdateBase
    elif issubclass(model, SemanticSpace):
        return _SemanticSpaceUpdateBase
    elif issubclass(model, Embedded):
        return _EmbeddedUpdateBase
    return None


def initialise_update_model(
    model: type[
        Document
        | Embedded
        | Entity
        | ReifiedRelation
        | ReifiedRelationDocument
        | Conjunction
        | SemanticSpace
    ],
) -> None:

    if not can_have_update_model(model):
        return

    # Checks if Update model has already been created; do not duplicate as we depend
    # on model reference!
    if "Update" in model.__dict__:
        return

    update_base_type = get_update_base_model_type(model)
    if not update_base_type:
        return

    model.Update = pydantic_create_model(  # ty:ignore[invalid-assignment]
        f"{model.__name__}Update",
        __base__=update_base_type,
        __module__=model.__module__,
        _owner=(ClassVar[model], model),
        __doc__=model._meta.description if model._meta.description else "",
        __config__=ConfigDict(alias_generator=to_camel),
        type=(Literal[model.__name__], Field(default=model.__name__)),  # type: ignore
    )  # pyright: ignore[reportAttributeAccessIssue]

    build_label_field_on_update_model(model.Update)

    model.Update.model_rebuild(force=True)


def build_label_field_on_update_model(
    create_model: type[_UpdateBase],
):

    if getattr(create_model._meta, "require_label", True):
        create_model.model_fields["label"] = FieldInfo(annotation=str)


def get_embedded_annotation_types(
    field_definition: EmbeddedFieldDefinition,
) -> UnionType:
    types = []
    for type_option in field_definition.type_options:
        types.append(type_option.annotated_type.Update)
        types.append(type_option.annotated_type.Create)

    return Union[*types]  # type: ignore


def add_fields_to_update_model(
    model: type[
        _DocumentUpdateBase
        | _EmbeddedUpdateBase
        | _EntityUpdateBase
        | _ReifiedRelationUpdateBase
        | _ReifiedRelationDocumentUpdateBase
        | _ConjunctionUpdateBase
        | _SemanticSpaceUpdateBase
    ],
    fields_to_bind: list,
) -> None:
    pass

    # Literal fields
    for field_name, field_definition in model._meta.fields.literal_fields.items():
        has_inherited_bindings = field_has_inherited_field_bindings(
            fields_to_bind, field_name, field_definition.field_on_model
        )
        if has_inherited_bindings:
            annotation = field_definition.annotated_type | None
        else:
            annotation = field_definition.annotated_type

        if field_definition.db_field:
            continue
        model.model_fields[field_name] = FieldInfo(
            annotation=annotation,
            validation_alias=to_camel(field_name),
            description=field_definition.description,
            **map_validators_to_kwargs(field_definition.validators),
        )
        if has_inherited_bindings:
            model.model_fields[field_name].default = None

    # Embedded fields
    for field_name, field_definition in model._meta.fields.embedded_fields.items():
        if field_definition.db_field:
            continue

        annotation = get_embedded_annotation_types(field_definition)

        has_inherited_bindings = field_has_inherited_field_bindings(
            fields_to_bind, field_name, field_definition.field_on_model
        )
        if has_inherited_bindings:
            annotation = annotation | None

        if annotation:
            model.model_fields[field_name] = FieldInfo(
                annotation=annotation,  # type: ignore
                validation_alias=to_camel(field_name),
                description=field_definition.description,
            )
        if has_inherited_bindings:
            model.model_fields[field_name].default = None

    model.model_rebuild(force=True)
