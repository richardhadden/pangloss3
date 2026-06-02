from typing import ClassVar, Literal

from pydantic import ConfigDict
from pydantic import create_model as pydantic_create_model
from pydantic.alias_generators import to_camel
from pydantic.fields import FieldInfo

from pangloss_models.model_bases.base_models import _DeclaredClass
from pangloss_models.model_bases.document import Document, _DocumentHeadViewBase
from pangloss_models.model_bases.entity import Entity, _EntityHeadViewBase
from pangloss_models.model_bases.reified_relation import (
    ReifiedRelationDocument,
    _ReifiedRelationDocumentHeadViewBase,
)


def can_have_head_view_model(model: type[_DeclaredClass]) -> bool:
    return issubclass(
        model,
        (
            Document,
            Entity,
            ReifiedRelationDocument,
        ),
    )


def get_head_view_base_model_type(
    model: type[Document | Entity | ReifiedRelationDocument],
) -> (
    type[
        _DocumentHeadViewBase
        | _EntityHeadViewBase
        | _ReifiedRelationDocumentHeadViewBase
    ]
    | None
):
    if issubclass(model, Document):
        return _DocumentHeadViewBase
    elif issubclass(model, Entity):
        return _EntityHeadViewBase
    elif issubclass(model, ReifiedRelationDocument):
        return _ReifiedRelationDocumentHeadViewBase


def build_label_field_on_head_view_model(
    head_view_model: type[
        _DocumentHeadViewBase
        | _EntityHeadViewBase
        | _ReifiedRelationDocumentHeadViewBase
    ],
):

    if getattr(head_view_model._meta, "require_label", True):
        head_view_model.model_fields["label"] = FieldInfo(annotation=str)


def initialise_head_view_model(
    model: type[Document | Entity | ReifiedRelationDocument],
) -> None:

    if not can_have_head_view_model(model):
        return

    # Checks if HeadView model has already been created;
    # do not duplicate as we depend on persistent model reference!
    if "HeadView" in model.__dict__:
        return

    # Extracts from the _DeclaredClass definition the annotation for .HeadView
    head_view_base_type = get_head_view_base_model_type(model)
    if not head_view_base_type:
        return

    model.HeadView = pydantic_create_model(  # ty:ignore[invalid-assignment]
        f"{model.__name__}HeadView",
        __base__=(head_view_base_type, model.View),
        __module__=model.__module__,
        _owner=(ClassVar[model], model),
        __doc__=model._meta.description if model._meta.description else "",
        __config__=ConfigDict(alias_generator=to_camel),
        type=(Literal[model.__name__], model.__name__),  # type: ignore
    )
    print("---")
    print(model)
    for field_name, field_info in model.View.model_fields.items():
        print(field_name)
        if field_name == "meta":
            continue
        model.HeadView.model_fields[field_name] = field_info

    model.HeadView.model_rebuild(force=True)
