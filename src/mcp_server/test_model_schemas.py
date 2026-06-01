# =============================================================================
# Unit Tests: src/mcp_server/model_schemas.py
# =============================================================================
# Validates the MODEL_SCHEMAS registry (database table schemas + SQL templates)
# and the PYDANTIC_SCHEMAS registry (Pydantic model JSON schemas).
# No cloud services or database connections required — pure dict/Pydantic logic.
#
# Run with:
#   poetry run pytest src/mcp_server/test_model_schemas.py -v
# =============================================================================

import pytest
import os
import sys

# The model_schemas module is imported at the top of this test file.
# It needs PROJECT_DIR and related env vars set for relative path resolution.
os.environ.setdefault("PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("AGENT_CARDS_DIR", os.path.join(os.environ["PROJECT_DIR"], "agent_cards"))
os.environ.setdefault("SQL_DIR", os.path.join(os.environ["PROJECT_DIR"], "src", "utils", "postgressql", "sql_library"))
os.environ.setdefault("USER_AGENT", "test-runner/1.0.0")

from src.mcp_server.model_schemas import (  # noqa: E402 — env must be set before import
    MODEL_SCHEMAS,
    PYDANTIC_SCHEMAS,
    build_cheatsheet,
    get_model_schema,
    get_pydantic_schema,
    list_model_names,
    list_pydantic_model_names,
)


# ── MODEL_SCHEMAS Registry ──────────────────────────────────────────────────

class TestModelSchemasRegistry:
    """The database table schema registry exposed via get_model_schema_tool."""

    def test_all_registered_models(self):
        """Every database-backed entity has a schema entry."""
        expected = [
            "blog_content",
            "content_strategy",
            "formatted_research_findings",
            "generated_query",
            "linkedin_account",
            "linkedin_post",
            "marketing_image",
            "research_finding",
            "research_project",
            "research_project_information",
        ]
        names = list_model_names()
        for model in expected:
            assert model in names, f"Missing database model: {model}"

    def test_every_model_has_table(self):
        """Every schema must declare a table_name."""
        for name, schema in MODEL_SCHEMAS.items():
            assert "table_name" in schema, f"{name} missing table_name"
            assert schema["table_name"].startswith("public."), (
                f"{name} table_name should be fully qualified: {schema['table_name']}"
            )

    def test_every_model_has_primary_key(self):
        """Every schema must declare a primary_key."""
        for name, schema in MODEL_SCHEMAS.items():
            assert "primary_key" in schema, f"{name} missing primary_key"

    def test_every_model_has_fields(self):
        """Every schema must have at least one field."""
        for name, schema in MODEL_SCHEMAS.items():
            assert len(schema["fields"]) > 0, f"{name} has no fields"

    def test_every_model_has_sql(self):
        """Every schema must have at least read and insert SQL templates."""
        for name, schema in MODEL_SCHEMAS.items():
            assert "sql" in schema, f"{name} missing sql"
            # Every model MUST have at least one read operation
            has_read = any("read" in op for op in schema["sql"])
            assert has_read, f"{name} has no read SQL operation"
            # Every model MUST have an insert operation
            assert "insert" in schema["sql"], f"{name} missing insert SQL"

    def test_fields_have_required_keys(self):
        """Every field dict must have name, type, pg_type, pg_nullable, description."""
        for name, schema in MODEL_SCHEMAS.items():
            for field in schema["fields"]:
                for key in ["name", "type", "pg_type", "pg_nullable", "description"]:
                    assert key in field, (
                        f"{name}.{field.get('name', '?')} missing key: {key}"
                    )

    def test_sql_operations_are_tuples(self):
        """Each SQL operation must be a (query_str, param_docs) tuple."""
        for name, schema in MODEL_SCHEMAS.items():
            for op_name, op_value in schema["sql"].items():
                assert isinstance(op_value, tuple), (
                    f"{name}.{op_name} should be a (query, params) tuple"
                )
                assert len(op_value) == 2, (
                    f"{name}.{op_name} tuple should have exactly 2 elements"
                )
                assert isinstance(op_value[0], str), (
                    f"{name}.{op_name} query must be a string"
                )
                assert isinstance(op_value[1], list), (
                    f"{name}.{op_name} param docs must be a list"
                )


# ── get_model_schema ────────────────────────────────────────────────────────

class TestGetModelSchema:
    """The MCP tool handler for fetching database schemas."""

    def test_known_model(self):
        """Returns the full schema for a registered model."""
        result = get_model_schema("research_project")
        assert "error" not in result
        assert result["model_name"] == "research_project"
        assert result["table_name"] == "public.research_projects"
        assert result["primary_key"] == "id"
        assert len(result["fields"]) > 0
        assert "sql" in result

    def test_case_insensitive(self):
        """Model name lookup is case-insensitive."""
        result = get_model_schema("Research_Project")
        assert "error" not in result
        assert result["model_name"] == "research_project"

    def test_unknown_model(self):
        """Returns a clear error dict instead of raising."""
        result = get_model_schema("nonexistent_table")
        assert "error" in result
        assert "nonexistent_table" in result["error"]
        assert "available_models" in result
        assert isinstance(result["available_models"], list)

    def test_available_models_listed(self):
        """The error response lists all available model names."""
        result = get_model_schema("bogus")
        available = result["available_models"]
        assert "research_project" in available
        assert "blog_content" in available


# ── list_model_names ────────────────────────────────────────────────────────

class TestListModelNames:
    """Lists all registered database model names."""

    def test_returns_sorted(self):
        """Names are sorted alphabetically."""
        names = list_model_names()
        assert names == sorted(names), "Model names should be sorted"

    def test_not_empty(self):
        """There are models registered."""
        assert len(list_model_names()) >= 9


# ── PYDANTIC_SCHEMAS Registry ───────────────────────────────────────────────

class TestPydanticSchemasRegistry:
    """The Pydantic model schema registry."""

    def test_core_models_registered(self):
        """Every major domain model is registered."""
        expected = [
            "ResearchProject",
            "ResearchProjectInformation",
            "ResearchFinding",
            "FormattedResearchFindings",
            "GeneratedQuery",
            "ContentStrategy",
            "BlogContent",
            "LinkedInPost",
            "LinkedInAccount",
            "MarketingImage",
            "ReportReviewCriteria",
            "PlannerResponseFormat",
            "PlannerTask",
            "TaskList",
            "AgentResponse",
            "WorkflowGraphSchema",
            "DeepResearchReport",
            "PineconeResults",
            "PineconeRetrievedDocument",
            # Tool args
            "BlogPostArgs",
            "PublishBlogPostArgs",
            "LinkedInPostArgs",
            "PineconeRetrieveArgs",
            "SerpApiSearchArgs",
            "PostgresQueryArgs",
            # SerpAPI
            "SerpApiOrganicResult",
            "FormattedSerpapiWebSearchResults",
        ]
        names = list_pydantic_model_names()
        for model in expected:
            assert model in names, f"Missing Pydantic model: {model}"

    def test_enums_registered(self):
        """Enums are registered alongside models."""
        names = list_pydantic_model_names()
        for enum_name in ["TaskStatus", "DeliverableStatusEnum", "QueryStatus", "WorkflowStatus"]:
            assert enum_name in names, f"Missing enum: {enum_name}"

    def test_all_models_are_pydantic(self):
        """Every registered entry must be a Pydantic BaseModel subclass."""
        from pydantic import BaseModel
        for name, cls in PYDANTIC_SCHEMAS.items():
            # Enums are not BaseModel subclasses — skip them
            if hasattr(cls, "model_fields"):
                if not issubclass(cls, BaseModel):
                    pytest.fail(f"{name} has model_fields but is not a BaseModel subclass")
            elif hasattr(cls, "model_json_schema"):
                # All Pydantic models have model_json_schema
                pass


# ── get_pydantic_schema ─────────────────────────────────────────────────────

class TestGetPydanticSchema:
    """The MCP tool handler for fetching Pydantic JSON schemas."""

    def test_known_model(self):
        """Returns JSON schema + field metadata."""
        result = get_pydantic_schema("BlogContent")
        assert "error" not in result
        assert result["model_name"] == "BlogContent"
        assert "json_schema" in result
        assert "fields" in result
        # BlogContent has 8 fields (id, research_project_id, title, content,
        # seo_keywords, publication_date, keywords_and_key_aspects, metadata)
        assert len(result["fields"]) == 8

    def test_field_structure(self):
        """Each field entry has name, type, required, description."""
        result = get_pydantic_schema("LinkedInPost")
        for field in result["fields"]:
            for key in ["name", "type", "required", "description"]:
                assert key in field, f"Field missing key: {key}"

    def test_json_schema_valid(self):
        """The returned JSON schema is a valid JSON Schema object."""
        import json
        result = get_pydantic_schema("ResearchProject")
        schema = result["json_schema"]
        assert schema.get("type") is not None
        assert "properties" in schema or schema.get("type") == "string"
        # Must be serializable
        json.dumps(schema)

    def test_pinecone_results(self):
        """PineconeResults has serialized and retrieved_docs fields."""
        result = get_pydantic_schema("PineconeResults")
        field_names = [f["name"] for f in result["fields"]]
        assert "serialized" in field_names
        assert "retrieved_docs" in field_names

    def test_pinecone_retrieved_document(self):
        """PineconeRetrievedDocument has page_content and metadata fields."""
        result = get_pydantic_schema("PineconeRetrievedDocument")
        field_names = [f["name"] for f in result["fields"]]
        assert "page_content" in field_names
        assert "metadata" in field_names

    def test_unknown_model(self):
        """Returns a clear error for unknown models."""
        result = get_pydantic_schema("FakeModel")
        assert "error" in result
        assert "FakeModel" in result["error"]


# ── list_pydantic_model_names ───────────────────────────────────────────────

class TestListPydanticModelNames:
    """Lists all registered Pydantic model names."""

    def test_returns_sorted(self):
        """Names are sorted alphabetically."""
        names = list_pydantic_model_names()
        assert names == sorted(names)

    def test_not_empty(self):
        """There are 50+ models registered."""
        assert len(list_pydantic_model_names()) >= 50


# ── build_cheatsheet ────────────────────────────────────────────────────────

class TestBuildCheatsheet:
    """Compact reference card for use in COT prompts."""

    def test_returns_string(self):
        """Returns a non-empty string."""
        cs = build_cheatsheet()
        assert isinstance(cs, str)
        assert len(cs) > 0

    def test_includes_all_models(self):
        """Every registered database model appears in the cheatsheet."""
        cs = build_cheatsheet()
        for name in list_model_names():
            assert name in cs, f"Cheatsheet missing model: {name}"

    def test_includes_instructions(self):
        """Tells agents to call get_model_schema_tool for full details."""
        cs = build_cheatsheet()
        assert "get_model_schema_tool" in cs.lower()
