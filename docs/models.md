Model Types
===========

Node Types
----------

### `Document`
(SHOULD documents be nestable?)
Describes a top-level viewable document (maps to node)

Inbound types:
- Create
- Update

Outbound types:
- View -- plain view model for embedded docs, inc. for editing
    - ID, Label
- HeadView
    - ID, Label, _meta, "context" (if nested?)
- ReferenceView
    - ID, Label, containing doc ref/type, in_semantic_spaces, 


### `Entity`
Describes an Entity, referenceable by a document (maps to node)

Inbound types:
- Create
- Update
- ReferenceSet
- ~~ReferenceCreate~~ Just use Create

Outbound types:
- UpdateView
    - ID, Label, _meta
- Head View
    - ID, Label, _meta, incoming relations
- ReferenceView
    - ID, Label, containing doc ref/type

### `ReifiedRelation`
Describes a relation to an Entity via an intermediate node

Inbound types:

- Create
- Update

Outbound types:
- View/UpdateView
    - ID, Label incoming relations

### `ReifiedRelationDocument`
Same as ReifiedRelation, but with label and treated as SubDocument

Inbound types:
- Create
- Update

Outbound types:
- View/UpdateView
    - ID, Label, created/modified, incoming relations

### `Embedded`
Same as SubDocument, but treated as intrinsic part of container

Inbound types:
- Create
- Update

Outbound types:
- View/UpdateView

### `SemanticSpace`

Inbound types:
- Create
- Update

Outbound types:
- View/UpdateView

### `Conjunction`

Inbound types:
- Create
- Update

Outbound types:
- View/UpdateView

### `Relation`
APIS-style relation-as-node


PropertyClasses
---------------

### `list[T]`
Literal list of type T

### `AnnotatedLiteral[Value]`
Provides extra literal fields that are bound to the main value

### `typing.TypedDict`
Flattened and stored as keys


Special Classes
---------------

### `ViaEdge[Target, EdgeModel]`
Adds an edge of type EdgeModel to a relation

### `Traits`
Mixin classes adding extra fields and labels

### `Fulfils[T, T, ...]`
Optionally include fields of a trait, that are fulfilled by being provided (thus adding label)

### DBField
Use with Annotated, labels a field as database-only (not returned by API), createable from existing fields on write

### APIField
Use with Annotated, labels a field as API-only (not in DB), createble from existing fields on read
