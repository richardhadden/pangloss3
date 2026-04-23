import heapq
from typing import ClassVar, get_args, get_origin

from pydantic import BaseModel


class ModelRegistry:
    """
    Deterministic model registry + dependency resolver.

    Responsibilities:
    - Register models
    - Build dependency graph (explicit + inferred)
    - Provide stable topological ordering
    - Finalise models (pydantic rebuild + user init hook)
    """

    @classmethod
    def _reset(cls):
        print("RESETTING")
        cls._models = []
        cls._model_set = set()

    _models: ClassVar[list[type[BaseModel]]] = []
    _model_set: ClassVar[set[type[BaseModel]]] = set()

    # ----------------------------
    # Registration
    # ----------------------------

    @classmethod
    def register(cls, model: type[BaseModel]) -> None:
        print("registering", model)
        if model not in cls._model_set:
            cls._models.append(model)
            cls._model_set.add(model)

        print(len(cls._model_set))

    @classmethod
    def all_models(cls) -> dict[str, type[BaseModel]]:
        return {m.__name__: m for m in cls._models}

    # ----------------------------
    # Dependency extraction
    # ----------------------------

    @classmethod
    def _explicit_deps(cls, model: type[BaseModel]) -> set[type[BaseModel]]:
        return set(getattr(model, "__depends_on__", []))

    @classmethod
    def _generic_deps(cls, model: type[BaseModel]) -> set[type[BaseModel]]:
        deps = set()

        meta = getattr(model, "__pydantic_generic_metadata__", None)
        if meta:
            for arg in meta.get("args", ()):
                if isinstance(arg, type) and issubclass(arg, BaseModel):
                    deps.add(arg)

        return deps

    @classmethod
    def _annotation_deps(cls, model: type[BaseModel]) -> set[type[BaseModel]]:
        """
        Optional light inference:
        Extract BaseModel types from annotations.
        """
        deps = set()

        for field in getattr(model, "model_fields", {}).values():
            ann = field.annotation

            stack = [ann]
            while stack:
                tp = stack.pop()

                if isinstance(tp, type) and issubclass(tp, BaseModel):
                    deps.add(tp)
                    continue

                origin = get_origin(tp)
                if origin:
                    stack.extend(get_args(tp))

        return deps

    @classmethod
    def _model_dependencies(cls, model: type[BaseModel]) -> list[type[BaseModel]]:
        deps = set()

        deps |= cls._explicit_deps(model)
        deps |= cls._generic_deps(model)
        deps |= cls._annotation_deps(model)

        # Only keep registered models and avoid self-dependency
        deps = {d for d in deps if d in cls._model_set and d is not model}

        return sorted(deps, key=cls._model_key)

    # ----------------------------
    # Graph
    # ----------------------------

    @classmethod
    def _model_key(cls, model: type[BaseModel]) -> str:
        return f"{model.__module__}.{model.__qualname__}"

    @classmethod
    def _build_graph(cls) -> dict[type[BaseModel], list[type[BaseModel]]]:
        graph = {}

        for model in sorted(cls._models, key=cls._model_key):
            graph[model] = cls._model_dependencies(model)

        return graph

    # ----------------------------
    # Topological sort (stable)
    # ----------------------------

    @classmethod
    def _toposort(cls, graph):
        indegree = {n: 0 for n in graph}

        for node, deps in graph.items():
            for dep in deps:
                indegree[node] += 1

        heap = []
        for node, deg in indegree.items():
            if deg == 0:
                heapq.heappush(heap, (cls._model_key(node), id(node), node))

        ordered = []

        while heap:
            _, _, node = heapq.heappop(heap)
            ordered.append(node)

            for other, deps in graph.items():
                if node in deps:
                    indegree[other] -= 1
                    if indegree[other] == 0:
                        heapq.heappush(heap, (cls._model_key(other), id(other), other))

        cyclic = {n for n in graph if indegree[n] > 0}
        del heap
        return ordered, cyclic

    # ----------------------------
    # Finalisation
    # ----------------------------

    @classmethod
    def finalise(cls, *, allow_cycles: bool = True):
        """
        1. Resolve Pydantic types
        2. Run topo-ordered initialisation
        """

        # --- Phase 1: Pydantic rebuild ---
        namespace = cls.all_models()

        for model in cls._models:
            model.model_rebuild(force=True, _types_namespace=namespace)

        # --- Phase 2: dependency ordering ---
        graph = cls._build_graph()
        order, cyclic = cls._toposort(graph)

        # --- Phase 3: initialise in order ---
        for model in order:
            # model.model_rebuild(force=True, _types_namespace=namespace)
            cls._initialise_model(model)

        # --- Phase 4: fallback for cycles ---
        for model in cyclic:
            # model.model_rebuild(force=True, _types_namespace=namespace)
            cls._initialise_model(model)

        return order

    # ----------------------------
    # Hook for your system
    # ----------------------------

    @classmethod
    def _initialise_model(cls, model: type[BaseModel]):
        """
        Override or monkey-patch this.
        """

        print("CALLING initialise model on", model.__name__)

        from pangloss_models.initialise_models.initialise_create_db_model import (
            add_fields_to_create_db_model,
            initialise_create_db_model,
        )
        from pangloss_models.initialise_models.initialise_create_model import (
            add_fields_to_create_model,
            initialise_create_model,
        )
        from pangloss_models.initialise_models.initialise_field_definitions import (
            initialise_field_definitions,
        )
        from pangloss_models.initialise_models.initialise_reference_models import (
            initialise_reference_set_model,
            initialise_reference_view_model,
        )

        initialise_field_definitions(model)

        initialise_reference_set_model(model)
        initialise_reference_view_model(model)

        initialise_create_model(model)

        add_fields_to_create_model(model.Create, [])

        initialise_create_db_model(model)

        add_fields_to_create_db_model(model)
