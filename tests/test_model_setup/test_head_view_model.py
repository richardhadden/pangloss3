from typing import no_type_check
from uuid import UUID

from pangloss_models import initialise
from pangloss_models.model_bases.base_models import _APIHeadMeta
from pangloss_models.model_bases.document import Document


@no_type_check
def test_document_has_head_view():
    class Statement(Document):
        name: str

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
