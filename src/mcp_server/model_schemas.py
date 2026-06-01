"""
Model Schema Registry
=====================
Central source of truth for all database table schemas, JSON field descriptions,
and SQL CRUD templates. Exposed to agents via the ``get_model_schema_tool`` MCP tool.

Each model entry contains:
  - table_name: PG table name
  - description: what the model represents
  - fields: list of {name, type, description, pg_type, pg_nullable}
  - sql: {read, insert, update, delete} — the exact inline SQL templates

Agents call ``get_model_schema_tool(model_name)`` to fetch this info dynamically
instead of carrying hundreds of KB of inline schema docs in their system prompts.
"""

from __future__ import annotations

import json
from typing import Any

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

MODEL_SCHEMAS: dict[str, dict[str, Any]] = {
    # =========================================================================
    # 1. Research Project
    # =========================================================================
    "research_project": {
        "table_name": "public.research_projects",
        "description": "Top-level record for a marketing research project / campaign.",
        "fields": [
            {"name": "id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
             "description": "Auto-generated unique identifier (UUID4). Pass NULL/None to auto-generate on INSERT."},
            {"name": "name", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Short name of the research project."},
            {"name": "query", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "The original research query or campaign goal provided by the user."},
            {"name": "description", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Brief description of the research project."},
            {"name": "created_at", "type": "timestamp", "pg_type": "TIMESTAMP", "pg_nullable": True,
             "description": "Auto-set on creation (CURRENT_TIMESTAMP)."},
            {"name": "updated_at", "type": "timestamp", "pg_type": "TIMESTAMP", "pg_nullable": True,
             "description": "Last update timestamp."},
            {"name": "end_date", "type": "timestamp", "pg_type": "TIMESTAMP", "pg_nullable": True,
             "description": "Date the project was completed or ended. NULL if ongoing."},
        ],
        "primary_key": "id",
        "sql": {
            "read_by_id": (
                "SELECT * FROM public.research_projects WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
            "read_all": (
                "SELECT * FROM public.research_projects ORDER BY created_at DESC",
                [],
            ),
            "insert": (
                "INSERT INTO public.research_projects (id, name, query, description, created_at, updated_at) "
                "VALUES (COALESCE($1, gen_random_uuid()), $2, $3, $4, $5, $6) RETURNING *",
                [
                    {"$1": "id (UUID, NULL=gen_random_uuid())"},
                    {"$2": "name (TEXT)"},
                    {"$3": "query (TEXT)"},
                    {"$4": "description (TEXT)"},
                    {"$5": "created_at (TIMESTAMP)"},
                    {"$6": "updated_at (TIMESTAMP)"},
                ],
            ),
            "update": (
                "UPDATE public.research_projects SET name=$2, description=$3, query=$4, "
                "end_date=$5, updated_at=CURRENT_TIMESTAMP WHERE id = $1 RETURNING *",
                [
                    {"$1": "id (UUID)"},
                    {"$2": "name (TEXT)"},
                    {"$3": "description (TEXT)"},
                    {"$4": "query (TEXT)"},
                    {"$5": "end_date (TIMESTAMP, NULL if not completed)"},
                ],
            ),
            "delete": (
                "DELETE FROM public.research_projects WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
        },
    },

    # =========================================================================
    # 2. Research Project Information
    # =========================================================================
    "research_project_information": {
        "table_name": "public.research_project_information",
        "description": "Full context, scope, framework, and deliverable metadata for a research project.",
        "fields": [
            {"name": "id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
             "description": "Auto-generated unique identifier. Pass NULL/None on INSERT."},
            {"name": "research_project_id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
             "description": "Foreign key to research_projects.id."},
            {"name": "research_topic", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "The research topic provided in the query."},
            {"name": "research_overview", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Brief overview of the research topic and its significance."},
            {"name": "research_objectives", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Specific objectives and goals. If a dict, convert to JSON string."},
            {"name": "research_scope", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Scope including limitations and constraints. If a dict, convert to JSON string."},
            {"name": "research_framework", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Framework categories used to guide research. If a dict, convert to JSON string."},
            {"name": "report_info", "type": "JSONB", "pg_type": "JSONB", "pg_nullable": True,
             "description": "Report deliverable metadata object: "
             "{report_name, report_tiny_url, report_long_url, created_at, updated_at, "
             "ai_score (float), ai_feedback, user_feedback, user_approved (bool)}"},
            {"name": "summary_info", "type": "JSONB", "pg_type": "JSONB", "pg_nullable": True,
             "description": "Summary deliverable metadata object: "
             "{summary_name, summary_tiny_url, summary_long_url, created_at, updated_at, "
             "ai_score (float), ai_feedback, user_feedback, user_approved (bool)}"},
            {"name": "bottom_count", "type": "integer", "pg_type": "INTEGER", "pg_nullable": True,
             "description": "Counter tracking how many times the Aspectuator returned 'BOTTOM' (no new queries). Defaults to 0."},
            {"name": "created_at", "type": "timestamp", "pg_type": "TIMESTAMP", "pg_nullable": True,
             "description": "Auto-set on creation."},
            {"name": "updated_at", "type": "timestamp", "pg_type": "TIMESTAMP", "pg_nullable": True,
             "description": "Auto-set on update."},
        ],
        "primary_key": "id",
        "sql": {
            "read_by_id": (
                "SELECT * FROM public.research_project_information WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
            "read_by_research_project_id": (
                "SELECT * FROM public.research_project_information "
                "WHERE research_project_id = $1",
                [{"$1": "research_project_id (UUID)"}],
            ),
            "read_all": (
                "SELECT * FROM public.research_project_information",
                [],
            ),
            "insert": (
                "INSERT INTO public.research_project_information "
                "(id, research_project_id, research_topic, research_overview, "
                "research_objectives, research_scope, research_framework, report_info, summary_info, bottom_count) "
                "VALUES (COALESCE($1, gen_random_uuid()), $2, $3, $4, $5, $6, $7, CAST($8 AS JSONB), CAST($9 AS JSONB), $10) RETURNING *",
                [
                    {"$1": "id (UUID, NULL=gen_random_uuid())"},
                    {"$2": "research_project_id (UUID)"},
                    {"$3": "research_topic (TEXT)"},
                    {"$4": "research_overview (TEXT)"},
                    {"$5": "research_objectives (TEXT — convert dict to JSON string)"},
                    {"$6": "research_scope (TEXT — convert dict to JSON string)"},
                    {"$7": "research_framework (TEXT — convert dict to JSON string)"},
                    {"$8": "report_info (JSONB — pass as dict, will be CAST to JSONB)"},
                    {"$9": "summary_info (JSONB — pass as dict, will be CAST to JSONB)"},
                    {"$10": "bottom_count (INTEGER, default 0)"},
                ],
            ),
            "update": (
                "UPDATE public.research_project_information "
                "SET research_topic=$2, research_overview=$3, research_objectives=$4, "
                "research_scope=$5, research_framework=$6, "
                "report_info=CAST($7 AS JSONB), summary_info=CAST($8 AS JSONB), "
                "research_project_id=$9, bottom_count=$10, updated_at=CURRENT_TIMESTAMP "
                "WHERE id = $1 RETURNING *",
                [
                    {"$1": "id (UUID)"},
                    {"$2": "research_topic (TEXT)"},
                    {"$3": "research_overview (TEXT)"},
                    {"$4": "research_objectives (TEXT)"},
                    {"$5": "research_scope (TEXT)"},
                    {"$6": "research_framework (TEXT)"},
                    {"$7": "report_info (JSONB — pass as dict)"},
                    {"$8": "summary_info (JSONB — pass as dict)"},
                    {"$9": "research_project_id (UUID)"},
                    {"$10": "bottom_count (INTEGER, default 0)"},
                ],
            ),
            "delete": (
                "DELETE FROM public.research_project_information WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
        },
    },

    # =========================================================================
    # 3. Research Findings
    # =========================================================================
    "research_finding": {
        "table_name": "public.research_findings",
        "description": "Individual research findings scraped from web sources and pushed to Pinecone.",
        "fields": [
            {"name": "id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
            "description": "Auto-generated unique identifier. Pass NULL/None on INSERT."},
            {"name": "research_project_id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
            "description": "Foreign key to research_projects.id."},
            {"name": "source", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
            "description": "Source / publication name or platform."},
            {"name": "author", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
            "description": "Author name(s)."},
            {"name": "pub_date", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
            "description": "Publication date as a string."},
            {"name": "title", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
            "description": "Title of the research finding / article."},
            {"name": "url", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
            "description": "URL of the source article."},
            {"name": "research_cycle_count", "type": "integer", "pg_type": "INTEGER", "pg_nullable": True,
            "description": "Which research cycle this finding belongs to (1-indexed). NULL if unassigned."},
        ],
        "primary_key": "id",
        "sql": {
            "read_by_id": (
                "SELECT * FROM public.research_findings WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
            "read_by_research_project_id": (
                "SELECT * FROM public.research_findings "
                "WHERE research_project_id = $1",
                [{"$1": "research_project_id (UUID)"}],
            ),
            "read_all": (
                "SELECT * FROM public.research_findings ORDER BY research_cycle_count",
                [],
            ),
            "insert": (
                "INSERT INTO public.research_findings "
                "(id, research_project_id, source, author, pub_date, title, url, research_cycle_count) "
                "VALUES (COALESCE($1, gen_random_uuid()), $2, $3, $4, $5, $6, $7, $8) RETURNING *",
                [
                    {"$1": "id (UUID, NULL=gen_random_uuid())"},
                    {"$2": "research_project_id (UUID)"},
                    {"$3": "source (TEXT)"},
                    {"$4": "author (TEXT)"},
                    {"$5": "pub_date (TEXT)"},
                    {"$6": "title (TEXT)"},
                    {"$7": "url (TEXT)"},
                    {"$8": "research_cycle_count (INTEGER)"},
                ],
            ),
            "batch_insert": (
                "INSERT INTO public.research_findings "
                "(id, research_project_id, source, author, pub_date, title, url, research_cycle_count) "
                "SELECT * FROM UNNEST($1::UUID[], $2::UUID[], $3::TEXT[], $4::TEXT[], "
                "$5::TEXT[], $6::TEXT[], $7::TEXT[], $8::INTEGER[]) "
                "AS t(id, research_project_id, source, author, pub_date, title, url, research_cycle_count) RETURNING *",
                [
                    {"$1": "id[] (UUID array)"},
                    {"$2": "research_project_id[] (UUID array)"},
                    {"$3": "source[] (TEXT array)"},
                    {"$4": "author[] (TEXT array)"},
                    {"$5": "pub_date[] (TEXT array)"},
                    {"$6": "title[] (TEXT array)"},
                    {"$7": "url[] (TEXT array)"},
                    {"$8": "research_cycle_count[] (INTEGER array)"},
                ],
            ),
            "delete": (
                "DELETE FROM public.research_findings WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
        },
    },

    # =========================================================================
    # 4. Formatted Research Findings
    # =========================================================================
    "formatted_research_findings": {
        "table_name": "public.formatted_research_findings",
        "description": "Individual research findings from web searches, stored for retrieval and analysis.",
        "fields": [
            {"name": "id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
             "description": "Auto-generated unique identifier. Pass NULL/None on INSERT."},
            {"name": "research_project_id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
             "description": "Foreign key to research_projects.id."},
            {"name": "title", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Title of the research finding / article."},
            {"name": "author", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Author name(s)."},
            {"name": "publication_date", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Publication date as a string."},
            {"name": "source", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Source / publication name or platform."},
            {"name": "finding_summary", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Concise summary of the finding (key for retrieval quality)."},
            {"name": "relevance_to_research_topic", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Why this finding is relevant to the research topic."},
            {"name": "source_url", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "URL (column name is source_url, maps to 'url' in the Python model)."},
            {"name": "keywords_and_key_aspects", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Keywords and key aspects extracted from the finding."},
            {"name": "research_cycle_count", "type": "integer", "pg_type": "INTEGER", "pg_nullable": True,
             "description": "Which research cycle this finding belongs to (0-indexed)."},
            {"name": "query", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "The search query that produced this finding."},
            {"name": "created_at", "type": "timestamp", "pg_type": "TIMESTAMP", "pg_nullable": True,
             "description": "Auto-set on creation."},
        ],
        "primary_key": "id",
        "sql": {
            "read_by_id": (
                "SELECT * FROM public.formatted_research_findings WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
            "read_by_research_project_id": (
                "SELECT * FROM public.formatted_research_findings "
                "WHERE research_project_id = $1 ORDER BY created_at DESC",
                [{"$1": "research_project_id (UUID)"}],
            ),
            "read_all": (
                "SELECT * FROM public.formatted_research_findings ORDER BY created_at DESC",
                [],
            ),
            "insert": (
                "INSERT INTO public.formatted_research_findings "
                "(id, research_project_id, title, author, publication_date, source, "
                "finding_summary, relevance_to_research_topic, source_url, "
                "keywords_and_key_aspects, research_cycle_count, query) "
                "VALUES (COALESCE($1, gen_random_uuid()), $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) RETURNING *",
                [
                    {"$1": "id (UUID, NULL=gen_random_uuid())"},
                    {"$2": "research_project_id (UUID)"},
                    {"$3": "title (TEXT)"},
                    {"$4": "author (TEXT)"},
                    {"$5": "publication_date (TEXT)"},
                    {"$6": "source (TEXT)"},
                    {"$7": "finding_summary (TEXT)"},
                    {"$8": "relevance_to_research_topic (TEXT)"},
                    {"$9": "source_url (TEXT — the URL of the source)"},
                    {"$10": "keywords_and_key_aspects (TEXT)"},
                    {"$11": "research_cycle_count (INTEGER)"},
                    {"$12": "query (TEXT)"},
                ],
            ),
            "batch_insert": (
                "INSERT INTO public.formatted_research_findings "
                "(id, research_project_id, title, author, publication_date, source, "
                "finding_summary, relevance_to_research_topic, source_url, "
                "keywords_and_key_aspects, research_cycle_count, query) "
                "SELECT id, research_project_id, title, author, publication_date, source, "
                "finding_summary, relevance_to_research_topic, source_url, "
                "keywords_and_key_aspects, research_cycle_count, query "
                "FROM UNNEST($1::UUID[], $2::UUID[], $3::TEXT[], $4::TEXT[], $5::DATE[], "
                "$6::TEXT[], $7::TEXT[], $8::TEXT[], $9::TEXT[], $10::TEXT[], "
                "$11::INTEGER[], $12::TEXT[]) "
                "AS t(id, research_project_id, title, author, publication_date, source, "
                "finding_summary, relevance_to_research_topic, source_url, "
                "keywords_and_key_aspects, research_cycle_count, query) RETURNING *",
                [
                    {"$1": "id[] (UUID array)"},
                    {"$2": "research_project_id[] (UUID array)"},
                    {"$3": "title[] (TEXT array)"},
                    {"$4": "author[] (TEXT array)"},
                    {"$5": "publication_date[] (DATE array)"},
                    {"$6": "source[] (TEXT array)"},
                    {"$7": "finding_summary[] (TEXT array)"},
                    {"$8": "relevance_to_research_topic[] (TEXT array)"},
                    {"$9": "source_url[] (TEXT array)"},
                    {"$10": "keywords_and_key_aspects[] (TEXT array)"},
                    {"$11": "research_cycle_count[] (INTEGER array)"},
                    {"$12": "query[] (TEXT array)"},
                ],
            ),
            "update": (
                "UPDATE public.formatted_research_findings "
                "SET research_project_id=$2, source=$3, title=$4, author=$5, "
                "relevance_to_research_topic=$6, publication_date=$7, source_url=$8, "
                "keywords_and_key_aspects=$9, query=$10, research_cycle_count=$11 "
                "WHERE id = $1 RETURNING *",
                [
                    {"$1": "id (UUID)"},
                    {"$2": "research_project_id (UUID)"},
                    {"$3": "source (TEXT)"},
                    {"$4": "title (TEXT)"},
                    {"$5": "author (TEXT)"},
                    {"$6": "relevance_to_research_topic (TEXT)"},
                    {"$7": "publication_date (TEXT)"},
                    {"$8": "source_url (TEXT)"},
                    {"$9": "keywords_and_key_aspects (TEXT)"},
                    {"$10": "query (TEXT)"},
                    {"$11": "research_cycle_count (INTEGER)"},
                ],
            ),
            "delete": (
                "DELETE FROM public.formatted_research_findings WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
        },
    },

    # =========================================================================
    # 4. Generated Query
    # =========================================================================
    "generated_query": {
        "table_name": "public.generated_queries",
        "description": "Search queries generated by the Aspectuator sub-agent during the research process.",
        "fields": [
            {"name": "id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
             "description": "Auto-generated unique identifier."},
            {"name": "research_project_id", "type": "UUID", "pg_type": "UUID", "pg_nullable": True,
             "description": "Foreign key to research_projects.id."},
            {"name": "generated_query", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "The search query string."},
            {"name": "research_cycle_count", "type": "integer", "pg_type": "INTEGER", "pg_nullable": False,
             "description": "Research cycle (0-indexed)."},
            {"name": "framework_category", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "Framework category this query covers."},
            {"name": "status", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "One of: 'candidate', 'verified', 'searched'."},
            {"name": "created_at", "type": "bigint", "pg_type": "BIGINT", "pg_nullable": False,
             "description": "Unix epoch timestamp (seconds)."},
            {"name": "updated_at", "type": "bigint", "pg_type": "BIGINT", "pg_nullable": False,
             "description": "Unix epoch timestamp (seconds)."},
        ],
        "primary_key": "id",
        "sql": {
            "read_all": (
                "SELECT * FROM public.generated_queries "
                "WHERE research_project_id = $1 ORDER BY created_at DESC",
                [{"$1": "research_project_id (UUID)"}],
            ),
            "insert": (
                "INSERT INTO public.generated_queries "
                "(id, research_project_id, generated_query, research_cycle_count, "
                "framework_category, status) "
                "VALUES (COALESCE($1, gen_random_uuid()), $2, $3, $4, $5, $6) RETURNING *",
                [
                    {"$1": "id (UUID, NULL=gen_random_uuid())"},
                    {"$2": "research_project_id (UUID)"},
                    {"$3": "generated_query (TEXT)"},
                    {"$4": "research_cycle_count (INTEGER)"},
                    {"$5": "framework_category (TEXT)"},
                    {"$6": "status (TEXT — 'candidate'|'verified'|'searched')"},
                ],
            ),
            "batch_insert": (
                "INSERT INTO public.generated_queries "
                "(id, research_project_id, generated_query, research_cycle_count, "
                "framework_category, status) "
                "SELECT id, research_project_id, generated_query, research_cycle_count, "
                "framework_category, status "
                "FROM UNNEST($1::UUID[], $2::UUID[], $3::TEXT[], $4::INTEGER[], "
                "$5::TEXT[], $6::TEXT[]) "
                "AS t(id, research_project_id, generated_query, research_cycle_count, "
                "framework_category, status) RETURNING *",
                [
                    {"$1": "id[] (UUID array)"},
                    {"$2": "research_project_id[] (UUID array)"},
                    {"$3": "generated_query[] (TEXT array)"},
                    {"$4": "research_cycle_count[] (INTEGER array)"},
                    {"$5": "framework_category[] (TEXT array)"},
                    {"$6": "status[] (TEXT array)"},
                ],
            ),
            "batch_update_status": (
                "UPDATE public.generated_queries "
                "SET status = 'searched', "
                "updated_at = EXTRACT(EPOCH FROM NOW())::BIGINT "
                "WHERE id = ANY($1::UUID[]) RETURNING *",
                [{"$1": "id[] (UUID array — marks all listed IDs as 'searched')"}],
            ),
            "update": (
                "UPDATE public.generated_queries SET research_project_id=$2, "
                "generated_query=$3, research_cycle_count=$4, framework_category=$5, "
                "status=$6, updated_at=$7 "
                "WHERE id = $1 RETURNING *",
                [
                    {"$1": "id (UUID)"},
                    {"$2": "research_project_id (UUID)"},
                    {"$3": "generated_query (TEXT)"},
                    {"$4": "research_cycle_count (INTEGER)"},
                    {"$5": "framework_category (TEXT)"},
                    {"$6": "status (TEXT)"},
                    {"$7": "updated_at (BIGINT — Unix epoch seconds)"},
                ],
            ),
            "delete": (
                "DELETE FROM public.generated_queries WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
        },
    },

    # =========================================================================
    # 5. Content Strategy
    # =========================================================================
    "content_strategy": {
        "table_name": "public.content_strategy",
        "description": "Content strategy plan for a research project / campaign.",
        "fields": [
            {"name": "id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
             "description": "Auto-generated unique identifier."},
            {"name": "research_project_id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
             "description": "Foreign key to research_projects.id."},
            {"name": "content_strategy", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "The full content strategy text / outline."},
            {"name": "content_strategy_overview", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "Brief overview of the content strategy."},
            {"name": "key_messages", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "Key messages to communicate. If a list/dict, convert to JSON string."},
            {"name": "target_audience", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "Target audience description. If a list/dict, convert to JSON string."},
            {"name": "content_formats_and_channels", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "Content formats and distribution channels. If list/dict, convert to JSON string."},
            {"name": "content_strategy_calendar", "type": "JSONB", "pg_type": "JSONB", "pg_nullable": False,
             "description": "Content calendar as a JSON array of scheduled items. Default: []."},
            {"name": "created_at", "type": "timestamptz", "pg_type": "TIMESTAMPTZ", "pg_nullable": True,
             "description": "Auto-set on creation."},
            {"name": "updated_at", "type": "timestamptz", "pg_type": "TIMESTAMPTZ", "pg_nullable": True,
             "description": "Auto-set on update."},
        ],
        "primary_key": "id",
        "sql": {
            "read_by_id": (
                "SELECT * FROM public.content_strategy WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
            "read_by_research_project_id": (
                "SELECT * FROM public.content_strategy "
                "WHERE research_project_id = $1 ORDER BY created_at DESC",
                [{"$1": "research_project_id (UUID)"}],
            ),
            "read_all": (
                "SELECT * FROM public.content_strategy ORDER BY created_at DESC",
                [],
            ),
            "insert": (
                "INSERT INTO public.content_strategy "
                "(id, research_project_id, content_strategy, content_strategy_overview, "
                "key_messages, target_audience, content_formats_and_channels, "
                "content_strategy_calendar) "
                "VALUES (COALESCE($1, gen_random_uuid()), $2, $3, $4, $5, $6, $7, CAST($8 AS JSONB)) RETURNING *",
                [
                    {"$1": "id (UUID, NULL=gen_random_uuid())"},
                    {"$2": "research_project_id (UUID)"},
                    {"$3": "content_strategy (TEXT)"},
                    {"$4": "content_strategy_overview (TEXT)"},
                    {"$5": "key_messages (TEXT — convert lists to JSON string)"},
                    {"$6": "target_audience (TEXT — convert lists to JSON string)"},
                    {"$7": "content_formats_and_channels (TEXT — convert lists to JSON string)"},
                    {"$8": "content_strategy_calendar (JSONB — pass as JSON array)"},
                ],
            ),
            "update": (
                "UPDATE public.content_strategy "
                "SET content_strategy=$1, content_strategy_overview=$2, "
                "key_messages=$3, target_audience=$4, "
                "content_formats_and_channels=$5, "
                "content_strategy_calendar=CAST($6 AS JSONB), "
                "updated_at=CURRENT_TIMESTAMP "
                "WHERE id = $7 RETURNING *",
                [
                    {"$1": "content_strategy (TEXT)"},
                    {"$2": "content_strategy_overview (TEXT)"},
                    {"$3": "key_messages (TEXT)"},
                    {"$4": "target_audience (TEXT)"},
                    {"$5": "content_formats_and_channels (TEXT)"},
                    {"$6": "content_strategy_calendar (JSONB)"},
                    {"$7": "id (UUID)"},
                ],
            ),
            "delete": (
                "DELETE FROM public.content_strategy WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
        },
    },

    # =========================================================================
    # 6. Blog Content
    # =========================================================================
    "blog_content": {
        "table_name": "public.blog_content",
        "description": "Blog post content with SEO metadata and lifecycle tracking.",
        "fields": [
            {"name": "id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
             "description": "Auto-generated unique identifier."},
            {"name": "research_project_id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
             "description": "Foreign key to research_projects.id."},
            {"name": "title", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "Title of the blog post."},
            {"name": "content", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "Main blog post content (HTML or markdown)."},
            {"name": "seo_keywords", "type": "text[]", "pg_type": "TEXT[]", "pg_nullable": True,
             "description": "List of SEO keywords. Pass as a plain string list (e.g. ['kw1', 'kw2'])."},
            {"name": "publication_date", "type": "bigint", "pg_type": "BIGINT", "pg_nullable": True,
             "description": "Scheduled publication date as Unix epoch seconds. NULL = not scheduled."},
            {"name": "keywords_and_key_aspects", "type": "text[]", "pg_type": "TEXT[]", "pg_nullable": True,
             "description": "Keywords and key aspects. Pass as a plain string list."},
            {"name": "metadata", "type": "JSONB", "pg_type": "JSONB", "pg_nullable": False,
             "description": "Lifecycle metadata object: "
             "{ai_score (float|null), ai_feedback (str|null), user_feedback (str|null), "
             "created_at (int|null), updated_at (int|null), output_folder (str|null), "
             "port (int|null), blog_name (str|null), status (str), "
             "long_url (str|null), tiny_url (str|null)}"},
        ],
        "primary_key": "id",
        "sql": {
            "read_by_id": (
                "SELECT * FROM public.blog_content WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
            "read_by_research_project_id": (
                "SELECT * FROM public.blog_content "
                "WHERE research_project_id = $1 "
                "ORDER BY (metadata->>'created_at') DESC NULLS LAST",
                [{"$1": "research_project_id (UUID)"}],
            ),
            "read_all": (
                "SELECT * FROM public.blog_content "
                "ORDER BY (metadata->>'created_at') DESC NULLS LAST",
                [],
            ),
            "insert": (
                "INSERT INTO public.blog_content "
                "(id, research_project_id, title, content, seo_keywords, "
                "publication_date, keywords_and_key_aspects, metadata) "
                "VALUES (COALESCE($1, gen_random_uuid()), $2, $3, $4, $5, $6, $7, CAST($8 AS JSONB)) RETURNING *",
                [
                    {"$1": "id (UUID, NULL=gen_random_uuid())"},
                    {"$2": "research_project_id (UUID)"},
                    {"$3": "title (TEXT)"},
                    {"$4": "content (TEXT — HTML or markdown)"},
                    {"$5": "seo_keywords (TEXT[] — e.g. ['kw1','kw2'])"},
                    {"$6": "publication_date (BIGINT — Unix epoch seconds, NULL if unscheduled)"},
                    {"$7": "keywords_and_key_aspects (TEXT[])"},
                    {"$8": "metadata (JSONB — pass as dict, will be CAST to JSONB)"},
                ],
            ),
            "update": (
                "UPDATE public.blog_content "
                "SET title=$2, content=$3, seo_keywords=$4, publication_date=$5, "
                "keywords_and_key_aspects=$6, metadata=metadata || CAST($7 AS JSONB) "
                "WHERE id = $1 RETURNING *",
                [
                    {"$1": "id (UUID)"},
                    {"$2": "title (TEXT)"},
                    {"$3": "content (TEXT)"},
                    {"$4": "seo_keywords (TEXT[])"},
                    {"$5": "publication_date (BIGINT)"},
                    {"$6": "keywords_and_key_aspects (TEXT[])"},
                    {"$7": "metadata (JSONB — merged with existing metadata using ||)"},
                ],
            ),
            "delete": (
                "DELETE FROM public.blog_content WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
        },
    },

    # =========================================================================
    # 7. LinkedIn Post
    # =========================================================================
    "linkedin_post": {
        "table_name": "public.linkedin_posts",
        "description": "LinkedIn post content with scheduling and lifecycle tracking.",
        "fields": [
            {"name": "id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
             "description": "Auto-generated unique identifier."},
            {"name": "author_urn", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "LinkedIn URN of the post author (e.g. 'urn:li:person:...')."},
            {"name": "text", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "Text content of the LinkedIn post."},
            {"name": "hashtags", "type": "text[]", "pg_type": "TEXT[]", "pg_nullable": True,
             "description": "Hashtags as a list of strings."},
            {"name": "image_url", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "URL of an attached image. NULL if no image."},
            {"name": "linkedin_post_id", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "LinkedIn's own post ID, set after publishing. NULL until posted."},
            {"name": "scheduled_time", "type": "bigint", "pg_type": "BIGINT", "pg_nullable": True,
             "description": "Unix epoch seconds for scheduled publish. NULL = publish immediately."},
            {"name": "research_project_id", "type": "UUID", "pg_type": "UUID", "pg_nullable": True,
             "description": "Foreign key to research_projects.id."},
            {"name": "metadata", "type": "JSONB", "pg_type": "JSONB", "pg_nullable": False,
             "description": "Lifecycle metadata: "
             "{posted (bool), post_removed (bool), post_removed_at (int|null), "
             "ai_score (float|null), ai_feedback (str|null), user_feedback (str|null), "
             "posted_at (int|null), updated_at (int|null), status (str)}"},
        ],
        "primary_key": "id",
        "sql": {
            "read_by_id": (
                "SELECT * FROM public.linkedin_posts WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
            "read_by_author_urn": (
                "SELECT * FROM public.linkedin_posts "
                "WHERE author_urn = $1 ORDER BY created_at DESC",
                [{"$1": "author_urn (TEXT)"}],
            ),
            "read_by_research_project_id": (
                "SELECT * FROM public.linkedin_posts "
                "WHERE research_project_id = $1 ORDER BY created_at DESC",
                [{"$1": "research_project_id (UUID)"}],
            ),
            "read_unposted": (
                "SELECT * FROM public.linkedin_posts "
                "WHERE (metadata->>'posted') IS DISTINCT FROM 'true' "
                "AND (metadata->>'post_removed') IS DISTINCT FROM 'true' "
                "ORDER BY scheduled_time ASC NULLS LAST",
                [],
            ),
            "insert": (
                "INSERT INTO public.linkedin_posts "
                "(id, author_urn, text, hashtags, image_url, scheduled_time, "
                "research_project_id, metadata) "
                "VALUES (COALESCE($1, gen_random_uuid()), $2, $3, $4, $5, $6, $7, CAST($8 AS JSONB)) RETURNING *",
                [
                    {"$1": "id (UUID, NULL=gen_random_uuid())"},
                    {"$2": "author_urn (TEXT — LinkedIn person URN)"},
                    {"$3": "text (TEXT)"},
                    {"$4": "hashtags (TEXT[] — e.g. ['#marketing','#ai'])"},
                    {"$5": "image_url (TEXT, NULL if none)"},
                    {"$6": "scheduled_time (BIGINT — Unix epoch seconds, NULL = immediate)"},
                    {"$7": "research_project_id (UUID, NULL if none)"},
                    {"$8": "metadata (JSONB — pass as dict)"},
                ],
            ),
            "update": (
                "UPDATE public.linkedin_posts "
                "SET text=$2, hashtags=$3, image_url=$4, scheduled_time=$5, "
                "metadata=metadata || jsonb_build_object('updated_at', "
                "CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT)) "
                "WHERE id = $1 RETURNING *",
                [
                    {"$1": "id (UUID)"},
                    {"$2": "text (TEXT)"},
                    {"$3": "hashtags (TEXT[])"},
                    {"$4": "image_url (TEXT)"},
                    {"$5": "scheduled_time (BIGINT)"},
                ],
            ),
            "mark_posted": (
                "UPDATE public.linkedin_posts "
                "SET linkedin_post_id=$2, "
                "metadata = metadata || jsonb_build_object("
                "'posted', true, "
                "'posted_at', CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT), "
                "'updated_at', CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT)) "
                "WHERE id = $1 RETURNING *",
                [
                    {"$1": "id (UUID)"},
                    {"$2": "linkedin_post_id (TEXT — LinkedIn's assigned post ID)"},
                ],
            ),
            "mark_removed": (
                "UPDATE public.linkedin_posts "
                "SET metadata = metadata || jsonb_build_object("
                "'post_removed', true, "
                "'post_removed_at', CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT), "
                "'updated_at', CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT)) "
                "WHERE id = $1 RETURNING *",
                [{"$1": "id (UUID)"}],
            ),
            "delete": (
                "DELETE FROM public.linkedin_posts WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
        },
    },

    # =========================================================================
    # 8. LinkedIn Account
    # =========================================================================
    "linkedin_account": {
        "table_name": "public.linkedin_accounts",
        "description": "LinkedIn account credentials and profile information.",
        "fields": [
            {"name": "id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
             "description": "Auto-generated unique identifier."},
            {"name": "account_id", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "LinkedIn member URN (UNIQUE, NOT NULL)."},
            {"name": "name", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "Display name of the account holder."},
            {"name": "author_urn", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "LinkedIn author URN for posting."},
            {"name": "email", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Email address associated with the account."},
            {"name": "access_token", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "OAuth access token. NULL if not authenticated."},
            {"name": "token_expires_at", "type": "timestamptz", "pg_type": "TIMESTAMPTZ", "pg_nullable": True,
             "description": "Token expiration timestamp."},
            {"name": "created_at", "type": "timestamp", "pg_type": "TIMESTAMP", "pg_nullable": True,
             "description": "Auto-set on creation."},
            {"name": "updated_at", "type": "timestamp", "pg_type": "TIMESTAMP", "pg_nullable": True,
             "description": "Auto-set on update."},
        ],
        "primary_key": "id",
        "sql": {
            "read_by_id": (
                "SELECT * FROM public.linkedin_accounts WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
            "read_by_account_id": (
                "SELECT * FROM public.linkedin_accounts WHERE account_id = $1",
                [{"$1": "account_id (TEXT — LinkedIn member URN)"}],
            ),
            "read_all": (
                "SELECT * FROM public.linkedin_accounts ORDER BY created_at DESC",
                [],
            ),
            "insert": (
                "INSERT INTO public.linkedin_accounts "
                "(id, account_id, name, author_urn, email, access_token, token_expires_at) "
                "VALUES (COALESCE($1, gen_random_uuid()), $2, $3, $4, $5, $6, $7) RETURNING *",
                [
                    {"$1": "id (UUID, NULL=gen_random_uuid())"},
                    {"$2": "account_id (TEXT — UNIQUE)"},
                    {"$3": "name (TEXT)"},
                    {"$4": "author_urn (TEXT)"},
                    {"$5": "email (TEXT)"},
                    {"$6": "access_token (TEXT, NULL if none)"},
                    {"$7": "token_expires_at (TIMESTAMPTZ, NULL if none)"},
                ],
            ),
            "update": (
                "UPDATE public.linkedin_accounts "
                "SET name=$2, author_urn=$3, email=$4, updated_at=CURRENT_TIMESTAMP "
                "WHERE id = $1 RETURNING *",
                [
                    {"$1": "id (UUID)"},
                    {"$2": "name (TEXT)"},
                    {"$3": "author_urn (TEXT)"},
                    {"$4": "email (TEXT)"},
                ],
            ),
            "update_token": (
                "UPDATE public.linkedin_accounts "
                "SET access_token=$2, token_expires_at=$3, updated_at=CURRENT_TIMESTAMP "
                "WHERE account_id = $1 RETURNING *",
                [
                    {"$1": "account_id (TEXT)"},
                    {"$2": "access_token (TEXT)"},
                    {"$3": "token_expires_at (TIMESTAMPTZ)"},
                ],
            ),
            "delete": (
                "DELETE FROM public.linkedin_accounts WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
        },
    },

    # =========================================================================
    # 9. Marketing Image
    # =========================================================================
    "marketing_image": {
        "table_name": "public.marketing_images",
        "description": "AI-generated marketing images with S3 storage metadata.",
        "fields": [
            {"name": "id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
             "description": "Auto-generated unique identifier."},
            {"name": "research_project_id", "type": "UUID", "pg_type": "UUID", "pg_nullable": False,
             "description": "Foreign key to research_projects.id."},
            {"name": "image_url", "type": "text", "pg_type": "TEXT", "pg_nullable": False,
             "description": "The long S3 URL where the image is stored."},
            {"name": "tiny_url", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Shortened URL for the image."},
            {"name": "description", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Text description used to generate the image."},
            {"name": "size_bytes", "type": "integer", "pg_type": "INTEGER", "pg_nullable": True,
             "description": "File size in bytes."},
            {"name": "img_dimensions", "type": "text", "pg_type": "TEXT", "pg_nullable": True,
             "description": "Image dimensions (e.g. '1024x1024')."},
            {"name": "created_at", "type": "timestamp", "pg_type": "TIMESTAMP", "pg_nullable": True,
             "description": "Auto-set on creation."},
            {"name": "saved_to_s3_at", "type": "timestamp", "pg_type": "TIMESTAMP", "pg_nullable": True,
             "description": "Timestamp when the image was uploaded to S3."},
            {"name": "updated_at", "type": "timestamp", "pg_type": "TIMESTAMP", "pg_nullable": True,
             "description": "Last update timestamp."},
        ],
        "primary_key": "id",
        "sql": {
            "read_by_id": (
                "SELECT * FROM public.marketing_images WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
            "read_by_research_project_id": (
                "SELECT * FROM public.marketing_images "
                "WHERE research_project_id = $1 ORDER BY created_at DESC",
                [{"$1": "research_project_id (UUID)"}],
            ),
            "read_all": (
                "SELECT * FROM public.marketing_images ORDER BY created_at DESC",
                [],
            ),
            "insert": (
                "INSERT INTO public.marketing_images "
                "(id, research_project_id, image_url, tiny_url, description, "
                "size_bytes, img_dimensions, created_at, saved_to_s3_at) "
                "VALUES (COALESCE($1, gen_random_uuid()), $2, $3, $4, $5, $6, $7, $8, $9) RETURNING *",
                [
                    {"$1": "id (UUID, NULL=gen_random_uuid())"},
                    {"$2": "research_project_id (UUID)"},
                    {"$3": "image_url (TEXT — S3 long URL)"},
                    {"$4": "tiny_url (TEXT, NULL if not yet generated)"},
                    {"$5": "description (TEXT)"},
                    {"$6": "size_bytes (INTEGER)"},
                    {"$7": "img_dimensions (TEXT — e.g. '1024x1024')"},
                    {"$8": "created_at (TIMESTAMP)"},
                    {"$9": "saved_to_s3_at (TIMESTAMP)"},
                ],
            ),
            "batch_insert": (
                "INSERT INTO public.marketing_images "
                "(id, research_project_id, image_url, tiny_url, description, "
                "size_bytes, img_dimensions, created_at, saved_to_s3_at) "
                "SELECT id, research_project_id, image_url, tiny_url, description, "
                "size_bytes, img_dimensions, created_at, saved_to_s3_at "
                "FROM UNNEST($1::UUID[], $2::UUID[], $3::TEXT[], $4::TEXT[], $5::TEXT[], "
                "$6::INTEGER[], $7::TEXT[], $8::TIMESTAMP[], $9::TIMESTAMP[]) "
                "AS t(id, research_project_id, image_url, tiny_url, description, "
                "size_bytes, img_dimensions, created_at, saved_to_s3_at) RETURNING *",
                [
                    {"$1": "id[] (UUID array)"},
                    {"$2": "research_project_id[] (UUID array)"},
                    {"$3": "image_url[] (TEXT array)"},
                    {"$4": "tiny_url[] (TEXT array, NULL for no tiny URL)"},
                    {"$5": "description[] (TEXT array)"},
                    {"$6": "size_bytes[] (INTEGER array)"},
                    {"$7": "img_dimensions[] (TEXT array — e.g. '1024x1024')"},
                    {"$8": "created_at[] (TIMESTAMP array)"},
                    {"$9": "saved_to_s3_at[] (TIMESTAMP array)"},
                ],
            ),
            "update": (
                "UPDATE public.marketing_images "
                "SET image_url=$2, tiny_url=$3, description=$4, size_bytes=$5, "
                "img_dimensions=$6, saved_to_s3_at=$7, updated_at=CURRENT_TIMESTAMP "
                "WHERE id = $1 RETURNING *",
                [
                    {"$1": "id (UUID)"},
                    {"$2": "image_url (TEXT)"},
                    {"$3": "tiny_url (TEXT)"},
                    {"$4": "description (TEXT)"},
                    {"$5": "size_bytes (INTEGER)"},
                    {"$6": "img_dimensions (TEXT)"},
                    {"$7": "saved_to_s3_at (TIMESTAMP)"},
                ],
            ),
            "delete": (
                "DELETE FROM public.marketing_images WHERE id = $1",
                [{"$1": "id (UUID)"}],
            ),
        },
    },
}


# ---------------------------------------------------------------------------
# Helper: list available model names
# ---------------------------------------------------------------------------
def list_model_names() -> list[str]:
    """Return all registered model names."""
    return sorted(MODEL_SCHEMAS.keys())


# ---------------------------------------------------------------------------
# Main entry point for the MCP tool
# ---------------------------------------------------------------------------
def get_model_schema(model_name: str) -> dict[str, Any]:
    """Return the full schema + SQL documentation for *model_name*.

    Returns ``{"error": "..."}`` when the model is not found, so the tool
    never raises and the agent sees a clear message.
    """
    model_name = model_name.strip().lower()
    schema = MODEL_SCHEMAS.get(model_name)
    if schema is None:
        return {
            "error": (
                f"Unknown model '{model_name}'. "
                f"Available models: {', '.join(list_model_names())}"
            ),
            "available_models": list_model_names(),
        }
    return {"model_name": model_name, **schema}


# ---------------------------------------------------------------------------
# Convenience: build a compact cheat-sheet for use in COT prompts
# ---------------------------------------------------------------------------
def build_cheatsheet() -> str:
    """Return a short reference card listing every model + its fields + SQL ops.

    This is ~1-2 KB instead of the ~250 KB currently in COT prompts.
    Agents that read this can then call ``get_model_schema_tool(name)`` for
    the full parameter-level detail when they actually need to run SQL.
    """
    lines = ["## Available Database Models\n"]
    lines.append(
        "Call ``get_model_schema_tool(model_name)`` for the complete field list "
        "and parameter-by-parameter SQL templates before running any SQL.\n"
    )
    for name, s in MODEL_SCHEMAS.items():
        pk = s["primary_key"]
        fields = ", ".join(f["name"] for f in s["fields"])
        ops = ", ".join(s["sql"].keys())
        lines.append(f"- **{name}**  ({s['table_name']}, PK={pk})")
        lines.append(f"  Fields: {fields}")
        lines.append(f"  SQL ops: {ops}")
    return "\n".join(lines)


# =============================================================================
# Pydantic Model Schemas
# =============================================================================
# Central registry of all Pydantic models used across the codebase.
# These provide type-safe data transfer objects for agents, tools, and APIs.
#
# Usage:
#   from mcp_server.model_schemas import get_pydantic_schema, PYDANTIC_SCHEMAS
#   schema = get_pydantic_schema("BlogContent")
#   # Or access directly: PYDANTIC_SCHEMAS["BlogContent"]
# =============================================================================

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Enums ───────────────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    """Status of a Planner task throughout its lifecycle."""
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    ERROR = "error"
    PENDING = "pending"
    INCOMPLETE = "incomplete"
    TODO = "todo"
    NOT_STARTED = "not_started"


class DeliverableStatusEnum(str, Enum):
    """Status of a deliverable (report, blog post, image, etc.) throughout its lifecycle."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_REVIEW = "waiting_for_review"
    NEEDS_REVISION = "needs_revision"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class QueryStatus(str, Enum):
    """Status of a generated search query in the research pipeline."""
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    SEARCHED = "searched"


class WorkflowStatus(str, Enum):
    """Execution status of a workflow graph."""
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


# ── Base / Configuration ────────────────────────────────────────────────────

class ServerConfig(BaseModel):
    """Configuration for running an agent or MCP server."""
    host: str = Field(default="localhost", description="The host to bind the server to.")
    port: int = Field(default=10101, description="The port to bind the server to.")
    transport: str = Field(
        default="streamable-http",
        description="Transport protocol: 'streamable-http', 'sse', or 'stdio'.",
    )
    path: str = Field(
        default="/mcp",
        description="URL path the MCP server is mounted at (e.g. /mcp, /tools/mcp, /agents/mcp).",
    )


class BaseAgentSchema(BaseModel):
    """Base class for all agents in the system."""
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    agent_name: str = Field(description="The name of the agent.")
    description: str = Field(description="Brief description of the agent's purpose and capabilities.")
    content_types: list[str] = Field(description="Supported content types for agent responses.")


# ── Research Project ────────────────────────────────────────────────────────

class ResearchProject(BaseModel):
    """Top-level record for a marketing research project / campaign."""
    id: UUID | None = Field(default=None, description="Auto-generated unique identifier (UUID4).")
    name: str | None = Field(default=None, description="Short name of the research project.")
    query: str = Field(..., description="The original research query or campaign goal provided by the user.")
    description: str | None = Field(default=None, description="Brief description of the research project.")
    created_at: datetime | None = Field(default=None, description="Auto-set on creation (CURRENT_TIMESTAMP).")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp.")
    end_date: datetime | None = Field(default=None, description="Date the project was completed or ended. NULL if ongoing.")


# ── Research Project Information ────────────────────────────────────────────

class ReportReviewCriteria(BaseModel):
    """Reusable AI + user review criteria for any deliverable.

    Included as a nested ``review_criteria`` field on ReportInfoMetadata,
    SummaryInfoMetadata, and any future deliverable metadata classes that
    need to track quality review state.
    """
    ai_score: float | None = Field(
        default=None,
        description="AI quality/comprehensiveness score based on objectives and framework.",
    )
    ai_feedback: str | None = Field(
        default=None, description="AI-generated feedback on the deliverable."
    )
    user_feedback: str | None = Field(
        default=None, description="User-provided feedback on the deliverable."
    )
    user_approved: bool = Field(
        default=False, description="Whether the user has approved the deliverable."
    )
    status: DeliverableStatusEnum = Field(
        default=DeliverableStatusEnum.NOT_STARTED,
        description="Current status of the deliverable in its lifecycle.",
    )


class ReportInfoMetadata(BaseModel):
    """Metadata for the research report deliverable."""
    report_name: str = Field(..., description="The name of the research report.")
    report_tiny_url: str = Field(..., description="Shortened URL where the report can be accessed.")
    report_long_url: str = Field(..., description="The long S3 URL where the report can be accessed.")
    content: str | None = Field(
        default=None,
        description="The full HTML content of the deliverable. Stored here so the user can pull "
                    "and view it directly from the site without querying blog_content separately.",
    )
    created_at: str = Field(..., description="ISO timestamp when the report was created.")
    updated_at: str = Field(..., description="ISO timestamp when the report was last updated.")
    review_criteria: ReportReviewCriteria = Field(
        default_factory=ReportReviewCriteria,
        description="AI and user review state for the report deliverable.",
    )


class SummaryInfoMetadata(BaseModel):
    """Metadata for the research summary deliverable."""
    summary_name: str = Field(..., description="The name of the research summary.")
    summary_tiny_url: str = Field(..., description="Shortened URL where the summary can be accessed.")
    summary_long_url: str = Field(..., description="The long S3 URL where the summary can be accessed.")
    content: str | None = Field(
        default=None,
        description="The full HTML content of the deliverable. Stored here so the user can pull "
                    "and view it directly from the site without querying blog_content separately.",
    )
    created_at: str = Field(..., description="ISO timestamp when the summary was created.")
    updated_at: str = Field(..., description="ISO timestamp when the summary was last updated.")
    review_criteria: ReportReviewCriteria = Field(
        default_factory=ReportReviewCriteria,
        description="AI and user review state for the summary deliverable.",
    )


class ResearchProjectInformation(BaseModel):
    """Full context, scope, framework, and deliverable metadata for a research project."""
    id: UUID | None = Field(default=None, description="Auto-generated unique identifier (UUID4).")
    research_project_id: UUID = Field(..., description="Foreign key to research_projects.id.")
    research_topic: str | None = Field(default=None, description="The research topic from the query.")
    research_overview: str | None = Field(default=None, description="Brief overview of the topic and its significance.")
    research_objectives: str | dict | None = Field(
        default=None,
        description="Specific objectives and goals. Stored as TEXT (JSON string) in the DB.",
    )
    research_scope: str | dict | None = Field(
        default=None,
        description="Scope including limitations and constraints. Stored as TEXT (JSON string) in the DB.",
    )
    research_framework: str | dict | None = Field(
        default=None,
        description="Framework categories used to guide research. Stored as TEXT (JSON string) in the DB.",
    )
    research_cycle_count: int = Field(default=0, description="Number of research cycles executed (0-indexed).")
    bottom_count: int = Field(default=0, description="Counter for how many times the Aspectuator returned 'BOTTOM' (no new queries).")
    report_info: ReportInfoMetadata | None = Field(default=None, description="Report deliverable metadata.")
    summary_info: SummaryInfoMetadata | None = Field(default=None, description="Summary deliverable metadata.")
    created_at: datetime | None = Field(default=None, description="Auto-set on creation.")
    updated_at: datetime | None = Field(default=None, description="Auto-set on update.")


# ── Research Findings ───────────────────────────────────────────────────────

class ResearchFinding(BaseModel):
    """Individual research finding scraped from a web source and pushed to Pinecone."""
    id: UUID | None = Field(default=None, description="Auto-generated unique identifier (UUID4).")
    research_project_id: UUID = Field(..., description="Foreign key to research_projects.id.")
    source: str | None = Field(default=None, description="Source / publication name or platform.")
    author: str | None = Field(default=None, description="Author name(s).")
    pub_date: str | None = Field(default=None, description="Publication date as a string.")
    title: str | None = Field(default=None, description="Title of the research finding / article.")
    url: str | None = Field(default=None, description="URL of the source article.")
    research_cycle_count: int | None = Field(
        default=None, description="Which research cycle (1-indexed). NULL if unassigned."
    )


class FormattedResearchFindings(BaseModel):
    """Formatted research finding with full metadata, stored for retrieval and analysis."""
    id: UUID | None = Field(default=None, description="Auto-generated unique identifier (UUID4).")
    research_project_id: UUID = Field(..., description="Foreign key to research_projects.id.")
    title: str | None = Field(default=None, description="Title of the research finding / article.")
    author: str | None = Field(default=None, description="Author name(s).")
    publication_date: str | None = Field(default=None, description="Publication date as a string.")
    source: str | None = Field(default=None, description="Source / publication name or platform.")
    finding_summary: str | None = Field(
        default=None, description="Concise summary of the finding (key for retrieval quality)."
    )
    relevance_to_research_topic: str | None = Field(
        default=None, description="Why this finding is relevant to the research topic."
    )
    source_url: str | None = Field(default=None, description="URL of the source.")
    keywords_and_key_aspects: str | None = Field(
        default=None, description="Keywords and key aspects extracted from the finding."
    )
    research_cycle_count: int = Field(default=0, description="Research cycle (0-indexed).")
    query: str | None = Field(default=None, description="The search query that produced this finding.")
    created_at: datetime | None = Field(default=None, description="Auto-set on creation.")


# ── Generated Query ─────────────────────────────────────────────────────────

class GeneratedQuery(BaseModel):
    """Search query generated by the Aspectuator sub-agent during research."""
    id: UUID | None = Field(default=None, description="Unique identifier for the generated query.")
    research_project_id: UUID | None = Field(default=None, description="Foreign key to research_projects.id.")
    generated_query: str = Field(..., description="The search query string.")
    research_cycle_count: int = Field(default=0, description="Research cycle (0-indexed).")
    framework_category: str = Field(..., description="Framework category this query covers.")
    status: QueryStatus = Field(default=QueryStatus.CANDIDATE, description="One of: 'candidate', 'verified', 'searched'.")
    created_at: int = Field(..., description="Unix epoch timestamp (seconds).")
    updated_at: int = Field(..., description="Unix epoch timestamp (seconds).")


# ── Content Strategy ────────────────────────────────────────────────────────

class ContentStrategyCalendarItem(BaseModel):
    """A single item in the content strategy calendar."""
    title: str | None = Field(default=None, description="Title of the content piece.")
    content_type: str | None = Field(default=None, description="Type: blog_post, linkedin_post, social_media, etc.")
    channel: str | None = Field(default=None, description="Distribution channel.")
    scheduled_date: str | None = Field(default=None, description="ISO date string for the scheduled publication.")
    status: str | None = Field(default=None, description="Status of the calendar item.")
    notes: str | None = Field(default=None, description="Additional notes.")


class ContentStrategy(BaseModel):
    """Content strategy plan for a research project / campaign."""
    id: UUID | None = Field(default=None, description="Auto-generated unique identifier (UUID4).")
    research_project_id: UUID = Field(..., description="Foreign key to research_projects.id.")
    content_strategy: str | None = Field(default=None, description="The full content strategy text / outline.")
    content_strategy_overview: str | None = Field(default=None, description="Brief overview of the content strategy.")
    key_messages: str | list[str] | None = Field(
        default=None,
        description="Key messages to communicate. Stored as TEXT (JSON string) in the DB.",
    )
    target_audience: str | list[str] | None = Field(
        default=None,
        description="Target audience description. Stored as TEXT (JSON string) in the DB.",
    )
    content_formats_and_channels: str | list[str] | None = Field(
        default=None,
        description="Content formats and distribution channels. Stored as TEXT (JSON string) in the DB.",
    )
    content_strategy_calendar: list[ContentStrategyCalendarItem] = Field(
        default_factory=list, description="Content calendar as a list of scheduled items. Stored as JSONB."
    )
    created_at: datetime | None = Field(default=None, description="Auto-set on creation.")
    updated_at: datetime | None = Field(default=None, description="Auto-set on update.")


# ── Blog Content ────────────────────────────────────────────────────────────

class BlogContentMetadata(BaseModel):
    """Lifecycle metadata for a blog post."""
    ai_score: float | None = Field(default=None, description="AI quality/engagement score for the blog content.")
    ai_feedback: str | None = Field(default=None, description="AI-generated feedback on the blog content.")
    user_feedback: str | None = Field(default=None, description="User-provided feedback on the blog content.")
    created_at: int | None = Field(default=None, description="Unix timestamp when the blog content was created.")
    updated_at: int | None = Field(default=None, description="Unix timestamp of the last update.")
    output_folder: str | None = Field(
        default=None, description="Output folder where blog content files are stored."
    )
    port: int | None = Field(
        default=None, description="Port number where the blog post is hosted after publishing."
    )
    blog_name: str | None = Field(
        default=None, description="Blog post name, used for URL and Docker container name when published."
    )
    status: DeliverableStatusEnum = Field(
        default=DeliverableStatusEnum.NOT_STARTED,
        description="Current status of the blog content in its lifecycle.",
    )
    long_url: str | None = Field(default=None, description="Long S3 URL where the blog can be accessed.")
    tiny_url: str | None = Field(
        default=None, description="Shortened URL, typically generated after publishing."
    )


class BlogContent(BaseModel):
    """Blog post content with SEO metadata and lifecycle tracking."""
    id: UUID = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for this blog content record.")  # noqa: F821
    research_project_id: UUID = Field(..., description="ID of the associated research project.")
    title: str = Field(..., description="Title of the blog post.")
    content: str = Field(
        ..., description="Main blog post content — well-structured and formatted (HTML or markdown)."
    )
    seo_keywords: list[str] = Field(
        default_factory=list, description="SEO keywords to incorporate into the content."
    )
    publication_date: int | None = Field(
        default=None, description="Unix timestamp for scheduled publication. NULL if not scheduled."
    )
    keywords_and_key_aspects: list[str] = Field(
        default_factory=list,
        description="Keywords and key aspects to highlight, derived from research findings.",
    )
    metadata: BlogContentMetadata = Field(
        default_factory=BlogContentMetadata,
        description="Lifecycle metadata: timestamps, scores, feedback, URLs, and status.",
    )


# ── LinkedIn ────────────────────────────────────────────────────────────────

class LinkedInPostMetadata(BaseModel):
    """Lifecycle metadata for a LinkedIn post."""
    posted: bool = Field(default=False, description="Whether the post has been published to LinkedIn.")
    post_removed: bool = Field(default=False, description="Whether the post has been removed from LinkedIn.")
    post_removed_at: int | None = Field(default=None, description="Unix timestamp when the post was removed.")
    ai_score: float | None = Field(default=None, description="AI quality/engagement score for the post.")
    ai_feedback: str | None = Field(default=None, description="AI-generated feedback on the post content.")
    user_feedback: str | None = Field(default=None, description="User-provided feedback on the post.")
    posted_at: int | None = Field(default=None, description="Unix timestamp when the post was published.")
    updated_at: int | None = Field(default=None, description="Unix timestamp of the last update.")
    status: DeliverableStatusEnum = Field(
        default=DeliverableStatusEnum.NOT_STARTED,
        description="Current status of the post in its lifecycle.",
    )


class LinkedInPost(BaseModel):
    """LinkedIn post content with scheduling and lifecycle tracking."""
    id: UUID = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for this post record.")  # noqa: F821
    author_urn: str = Field(..., description="LinkedIn URN of the post author (e.g. 'urn:li:person:...').")
    text: str = Field(..., description="Text content of the LinkedIn post.")
    hashtags: list[str] = Field(default_factory=list, description="Hashtags included in the post.")
    image_url: str | None = Field(default=None, description="URL of the attached image. NULL if no image.")
    linkedin_post_id: str | None = Field(
        default=None, description="LinkedIn's own post ID, set after publishing. NULL until posted."
    )
    scheduled_time: int | None = Field(
        default=None, description="Unix epoch seconds for scheduled publish. NULL = publish immediately."
    )
    research_project_id: UUID | None = Field(
        default=None, description="ID of the associated research project. NULL if none."
    )
    metadata: LinkedInPostMetadata = Field(
        default_factory=LinkedInPostMetadata,
        description="Post lifecycle metadata: posting status, timestamps, AI and user feedback.",
    )


class LinkedInAccount(BaseModel):
    """LinkedIn account credentials and profile information."""
    id: UUID | None = Field(default=None, description="Auto-generated unique identifier (UUID4).")
    account_id: str = Field(..., description="LinkedIn member URN (UNIQUE, NOT NULL).")
    name: str = Field(..., description="Display name of the account holder.")
    author_urn: str | None = Field(default=None, description="LinkedIn author URN for posting.")
    email: str | None = Field(default=None, description="Email address associated with the account.")
    access_token: str | None = Field(default=None, description="OAuth access token. NULL if not authenticated.")
    token_expires_at: datetime | None = Field(default=None, description="Token expiration timestamp.")
    created_at: datetime | None = Field(default=None, description="Auto-set on creation.")
    updated_at: datetime | None = Field(default=None, description="Auto-set on update.")


# ── Marketing Images ────────────────────────────────────────────────────────

class MarketingImageMetadata(BaseModel):
    """Lifecycle metadata for a marketing image."""
    created_at: datetime | None = Field(
        default=None, description="Timestamp when the image generation request was initiated."
    )
    saved_to_s3_at: datetime | None = Field(
        default=None, description="Timestamp when the image was successfully uploaded to S3."
    )
    size_bytes: int | None = Field(default=None, description="Size of the image file in bytes.")
    img_dimensions: str | None = Field(
        default=None, description="Image dimensions as a string, e.g. '1024x1024'."
    )
    updated_at: datetime | None = Field(default=None, description="Timestamp of the last update.")


class MarketingImage(BaseModel):
    """AI-generated marketing image with S3 storage metadata."""
    id: UUID = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for this image record.")  # noqa: F821
    research_project_id: UUID = Field(..., description="ID of the associated research project.")
    image_url: str = Field(..., description="The long S3 URL where the image is stored.")
    tiny_url: str | None = Field(default=None, description="Shortened URL for the image.")
    description: str | None = Field(default=None, description="Text description used to generate the image.")
    metadata: MarketingImageMetadata = Field(
        default_factory=MarketingImageMetadata,
        description="Image lifecycle metadata: timestamps, file size, and dimensions.",
    )


# ── Keywords and Key Aspects ────────────────────────────────────────────────

class KeywordsAndKeyAspects(BaseModel):
    """Keywords and key aspects extracted during research."""
    id: UUID | None = Field(default=None, description="Unique identifier.")
    research_project_id: UUID = Field(..., description="ID of the associated research project.")
    keywords_and_key_aspects: list[str] = Field(..., description="List of keywords and key aspects.")
    research_cycle_count: int = Field(default=1, description="Count of the research cycle (1-indexed).")
    created_at: int = Field(..., description="Unix epoch timestamp when created.")
    updated_at: int = Field(..., description="Unix epoch timestamp when last updated.")


# ── Planner / Task Types ────────────────────────────────────────────────────

class PlannerTask(BaseModel):
    """A single task generated by the PlannerAgent."""
    id: int = Field(description="Unique identifier for the task within the plan.")
    description: str = Field(description="Brief and clear description of the task to be executed.")
    research_project_id: str | None = Field(
        default=None, description="The research_project_id for this campaign."
    )
    status: TaskStatus = Field(
        default=TaskStatus.INPUT_REQUIRED, description="Current status of the task."
    )


class TaskList(BaseModel):
    """A list of tasks generated by the PlannerAgent, executed sequentially."""
    original_query: str | None = Field(default=None, description="The original user query for context.")
    research_project_id: str | None = Field(
        default=None, description="The research_project_id for this campaign."
    )
    research_context: str | None = Field(
        default=None, description="Contextual information or research project related to the tasks."
    )
    tasks: list[PlannerTask] = Field(
        default_factory=list, description="List of tasks to be executed sequentially."
    )


class PlannerResponseFormat(BaseModel):
    """Structured response format for the PlannerAgent."""
    research_project_id: str | None = Field(
        default=None, description="The research_project_id for this campaign."
    )
    status: Literal["input_required", "completed", "error"] = Field(
        default="input_required",
        description=(
            "Status of the agent's response. 'input_required' = needs more info from user. "
            "'completed' = task done with final response. 'error' = an error occurred."
        ),
    )
    question: str | dict = Field(
        default="", description="Input needed from the user to generate the plan."
    )
    content: TaskList = Field(
        default_factory=TaskList,
        description="List of tasks generated by the PlannerAgent to be executed sequentially.",
    )


# ── Agent Response ──────────────────────────────────────────────────────────

class AgentResponse(BaseModel):
    """Generic output schema for any agent's response."""
    content: str | dict = Field(
        description="The content of the agent's response — string or structured dictionary."
    )
    is_task_complete: bool = Field(description="Whether the task associated with this response is complete.")
    require_user_input: bool = Field(
        description="Whether the agent requires additional user input to proceed."
    )


class AgentStreamChunk(BaseModel):
    """A single chunk emitted during an agent's streaming execution."""
    response_type: Literal["text", "data"] = Field(
        default="text", description="Type of the chunk: 'text' for prose, 'data' for structured objects."
    )
    is_task_complete: bool = Field(
        default=False, description="Whether the overall task is complete after this chunk."
    )
    require_user_input: bool = Field(
        default=False, description="Whether the agent needs user input to continue."
    )
    research_project_id: str | None = Field(default=None, description="Associated research project ID.")
    content: str | dict | None = Field(default=None, description="The chunk payload.")


# ── Workflow Graph ──────────────────────────────────────────────────────────

class WorkflowNodeSchema(BaseModel):
    """A single node in the workflow DAG representing one A2A task."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique node identifier.")  # noqa: F821
    task: str = Field(..., description="Description of the task for this node.")
    node_key: str | None = Field(default=None, description="Logical key for the node (e.g. 'planner').")
    node_label: str | None = Field(default=None, description="Human-readable label for the node.")
    agent_url: str | None = Field(default=None, description="Resolved A2A agent URL for this node.")
    agent_name: str | None = Field(default=None, description="Name of the agent handling this node.")
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary node attributes (task_id, context_id, query, etc.).",
    )


class WorkflowGraphSchema(BaseModel):
    """A directed acyclic graph (DAG) of workflow nodes representing a multi-agent pipeline."""
    nodes: dict[str, WorkflowNodeSchema] = Field(
        default_factory=dict, description="All nodes in the graph keyed by node ID."
    )
    edges: list[tuple[str, str]] = Field(
        default_factory=list, description="Directed edges as (from_node_id, to_node_id) tuples."
    )
    state: WorkflowStatus = Field(default=WorkflowStatus.INITIALIZED, description="Current execution state.")
    pause_node_id: str | None = Field(default=None, description="Node ID where the workflow is paused (if PAUSED).")
    entry_node_id: str | None = Field(default=None, description="The first node to execute.")


# ── Tool Argument Schemas ───────────────────────────────────────────────────

class LinkMetadata(BaseModel):
    """Metadata for a web link to be scraped and indexed."""
    title: str = Field(description="Title of the article/page.")
    author: str = Field(description="Author name.")
    date: str = Field(description="Publication date.")
    source: str = Field(description="Source URL or platform name.")


class ScrapeAndPushArgs(BaseModel):
    """Arguments for the Pinecone scrape-and-push operation."""
    result_dict: dict[str, LinkMetadata] = Field(
        description="Mapping of URL to its metadata for each link to scrape and index."
    )


class ImageGenerationArgs(BaseModel):
    """Arguments for the image generation tool."""
    description: str = Field(..., description="Text description for the image to generate.")


class SaveToS3Args(BaseModel):
    """Arguments for saving an image to S3."""
    image_data: str = Field(..., description="Base64-encoded image data.")
    filename: str = Field(..., description="Filename for the S3 object.")


class ImageUrlInput(BaseModel):
    """Input for a tool that accepts an image URL and returns a tiny URL."""
    image_url: str = Field(..., description="Long image URL to be shortened.")


class BlogPostArgs(BaseModel):
    """Arguments for blog post preview generation."""
    blog_content: str = Field(..., description="Full blog post content (HTML or markdown).")
    title: str = Field(..., description="Title of the blog post.")
    research_project_id: str = Field(..., description="ID of the associated research project.")


class ClearBlogPreviewArgs(BaseModel):
    """Arguments for clearing a blog post preview."""
    research_project_id: str = Field(..., description="ID of the research project whose preview to clear.")


class PublishBlogPostArgs(BaseModel):
    """Arguments for publishing a blog post via Docker."""
    blog_content: str = Field(..., description="Full blog post content (HTML).")
    title: str = Field(..., description="Title of the blog post.")
    research_project_id: str = Field(..., description="ID of the associated research project.")
    port: int = Field(..., description="Port number to host the blog post on.")
    blog_name: str = Field(..., description="Blog post name, used for the URL and Docker container name.")


class BlogNameArg(BaseModel):
    """Argument for Docker container operations identified by blog name."""
    blog_name: str = Field(..., description="Name of the blog post / Docker container.")


class LinkedInPostArgs(BaseModel):
    """Arguments for posting to LinkedIn."""
    author_urn: str = Field(..., description="LinkedIn URN of the post author.")
    text: str = Field(..., description="Text content of the LinkedIn post.")
    hashtags: list[str] = Field(default_factory=list, description="Hashtags to include.")
    image_url: str | None = Field(default=None, description="URL of an image to attach.")


class EditLinkedInPostArgs(BaseModel):
    """Arguments for editing an existing LinkedIn post."""
    linkedin_post_id: str = Field(..., description="LinkedIn's post ID to edit.")
    text: str = Field(..., description="New text content.")
    hashtags: list[str] = Field(default_factory=list, description="New hashtags.")


class DeleteLinkedInPostArgs(BaseModel):
    """Arguments for deleting a LinkedIn post."""
    linkedin_post_id: str = Field(..., description="LinkedIn's post ID to delete.")


class PineconeRetrieveArgs(BaseModel):
    """Arguments for querying the Pinecone vector store."""
    query: str = Field(..., description="Search query for vector similarity retrieval.")


class SerpApiSearchArgs(BaseModel):
    """Arguments for web search via SerpAPI."""
    query: str = Field(..., description="Search query string.")
    research_project_id: str = Field(..., description="ID of the associated research project.")


class PostgresQueryArgs(BaseModel):
    """Arguments for running a SQL query against the PostgreSQL database."""
    query: str = Field(..., description="The SQL statement (SELECT, INSERT, UPDATE, DELETE, etc.).")
    sql_params: list[Any] = Field(
        default_factory=list,
        description="Flat list of positional values bound to $1, $2, ... placeholders.",
    )
    fetch: bool = Field(default=True, description="True to return rows, False for statement status.")


# ── SerpAPI Result Schemas ──────────────────────────────────────────────────

class SerpApiOrganicResult(BaseModel):
    """An individual organic search result from SerpAPI."""
    position: int | None = Field(default=None, description="Rank position in search results.")
    title: str | None = Field(default=None, description="Title of the result.")
    link: str | None = Field(default=None, description="URL of the result.")
    snippet: str | None = Field(default=None, description="Text snippet from the result.")
    source: str | None = Field(default=None, description="Source domain or platform.")
    date: str | None = Field(default=None, description="Publication date if available.")


class FormattedSerpapiWebSearchResults(BaseModel):
    """Formatted SerpAPI search results ready for agent consumption."""
    query: str = Field(..., description="The search query that produced these results.")
    research_project_id: str = Field(..., description="ID of the associated research project.")
    organic_results: list[SerpApiOrganicResult] = Field(
        default_factory=list, description="List of organic search results."
    )
    total_results: int | None = Field(default=None, description="Approximate total number of results.")
    search_time: float | None = Field(default=None, description="Search execution time in seconds.")


# ── Pinecone Vector Store Schemas ────────────────────────────────────────────


class PineconeRetrievedDocument(BaseModel):
    """A single document retrieved from the Pinecone vector store.

    This is a JSON-serializable representation of a LangChain Document so that
    Pinecone results can be passed over MCP without relying on non-serializable
    LangChain internals.
    """
    page_content: str = Field(..., description="The text content of the retrieved document chunk.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Document metadata (source URL, title, chunk index, etc.).",
    )

    @classmethod
    def from_langchain_document(cls, doc: Any) -> "PineconeRetrievedDocument":
        """Convert a LangChain Document into a PineconeRetrievedDocument."""
        return cls(
            page_content=doc.page_content,
            metadata=dict(doc.metadata) if doc.metadata else {},
        )


class PineconeResults(BaseModel):
    """Results from a Pinecone vector-store similarity search.

    Two retrieval modes are available via the MCP tools:
    - ``retrieve_research_information_serialized`` — returns ``serialized`` as a
      single newline-joined string; ``retrieved_docs`` is None.
    - ``retrieve_research_information_documents`` — returns ``retrieved_docs`` as
      a list of structured documents; ``serialized`` is None.
    """
    serialized: str | None = Field(
        default=None,
        description=(
            "All retrieved documents joined into a single string with format "
            "'Source: {metadata}\\nContent: {page_content}' per document. "
            "None when the 'documents' variant is used."
        ),
    )
    retrieved_docs: list[PineconeRetrievedDocument] | None = Field(
        default=None,
        description=(
            "List of structured documents retrieved from the vector store, "
            "each with page_content and metadata. None when the 'serialized' variant is used."
        ),
    )


# ── Research Report Schemas ─────────────────────────────────────────────────

class DeepResearchReportSection(BaseModel):
    """A single section within a deep research report."""
    heading: str = Field(..., description="Section heading/title.")
    content: str = Field(..., description="Section body content.")
    sources: list[str] = Field(default_factory=list, description="Source URLs cited in this section.")
    key_findings: list[str] = Field(default_factory=list, description="Key findings in this section.")


class DeepResearchReport(BaseModel):
    """A complete deep research report with multiple sections."""
    title: str = Field(..., description="Report title.")
    research_project_id: str = Field(..., description="ID of the associated research project.")
    executive_summary: str = Field(..., description="Executive summary of the report.")
    sections: list[DeepResearchReportSection] = Field(
        default_factory=list, description="Report sections."
    )
    conclusion: str | None = Field(default=None, description="Report conclusion.")
    recommendations: list[str] = Field(default_factory=list, description="Actionable recommendations.")
    sources: list[str] = Field(default_factory=list, description="All sources cited in the report.")
    generated_at: datetime | None = Field(default=None, description="Timestamp when the report was generated.")


# =============================================================================
# Pydantic Schema Registry
# =============================================================================

PYDANTIC_SCHEMAS: dict[str, type[BaseModel]] = {
    # ── Enums ──
    "TaskStatus": TaskStatus,
    "DeliverableStatusEnum": DeliverableStatusEnum,
    "QueryStatus": QueryStatus,
    "WorkflowStatus": WorkflowStatus,
    # ── Configuration ──
    "ServerConfig": ServerConfig,
    "BaseAgentSchema": BaseAgentSchema,
    # ── Research ──
    "ResearchProject": ResearchProject,
    "ResearchProjectInformation": ResearchProjectInformation,
    "ReportInfoMetadata": ReportInfoMetadata,
    "SummaryInfoMetadata": SummaryInfoMetadata,
    "ReportReviewCriteria": ReportReviewCriteria,
    "ResearchFinding": ResearchFinding,
    "FormattedResearchFindings": FormattedResearchFindings,
    "GeneratedQuery": GeneratedQuery,
    "KeywordsAndKeyAspects": KeywordsAndKeyAspects,
    # ── Content Strategy ──
    "ContentStrategy": ContentStrategy,
    "ContentStrategyCalendarItem": ContentStrategyCalendarItem,
    # ── Blog ──
    "BlogContent": BlogContent,
    "BlogContentMetadata": BlogContentMetadata,
    # ── LinkedIn ──
    "LinkedInPost": LinkedInPost,
    "LinkedInPostMetadata": LinkedInPostMetadata,
    "LinkedInAccount": LinkedInAccount,
    # ── Images ──
    "MarketingImage": MarketingImage,
    "MarketingImageMetadata": MarketingImageMetadata,
    # ── Planner / Tasks ──
    "PlannerTask": PlannerTask,
    "TaskList": TaskList,
    "PlannerResponseFormat": PlannerResponseFormat,
    # ── Agent Communication ──
    "AgentResponse": AgentResponse,
    "AgentStreamChunk": AgentStreamChunk,
    # ── Workflow ──
    "WorkflowNodeSchema": WorkflowNodeSchema,
    "WorkflowGraphSchema": WorkflowGraphSchema,
    # ── Tool Arguments ──
    "LinkMetadata": LinkMetadata,
    "ScrapeAndPushArgs": ScrapeAndPushArgs,
    "ImageGenerationArgs": ImageGenerationArgs,
    "SaveToS3Args": SaveToS3Args,
    "ImageUrlInput": ImageUrlInput,
    "BlogPostArgs": BlogPostArgs,
    "ClearBlogPreviewArgs": ClearBlogPreviewArgs,
    "PublishBlogPostArgs": PublishBlogPostArgs,
    "BlogNameArg": BlogNameArg,
    "LinkedInPostArgs": LinkedInPostArgs,
    "EditLinkedInPostArgs": EditLinkedInPostArgs,
    "DeleteLinkedInPostArgs": DeleteLinkedInPostArgs,
    "PineconeRetrieveArgs": PineconeRetrieveArgs,
    "SerpApiSearchArgs": SerpApiSearchArgs,
    "PostgresQueryArgs": PostgresQueryArgs,
    # ── SerpAPI ──
    "SerpApiOrganicResult": SerpApiOrganicResult,
    "FormattedSerpapiWebSearchResults": FormattedSerpapiWebSearchResults,
    # ── Research Reports ──
    "DeepResearchReport": DeepResearchReport,
    "DeepResearchReportSection": DeepResearchReportSection,
    # ── Pinecone ──
    "PineconeResults": PineconeResults,
    "PineconeRetrievedDocument": PineconeRetrievedDocument,
}


def list_pydantic_model_names() -> list[str]:
    """Return all registered Pydantic model names."""
    return sorted(PYDANTIC_SCHEMAS.keys())


def get_pydantic_schema(model_name: str) -> dict[str, Any]:
    """Return the JSON schema for a Pydantic model by name.

    Returns ``{"error": "..."}`` when the model is not found, so the tool
    never raises and the agent sees a clear message.
    """
    model_name = model_name.strip()
    model_class = PYDANTIC_SCHEMAS.get(model_name)
    if model_class is None:
        return {
            "error": (
                f"Unknown Pydantic model '{model_name}'. "
                f"Available models: {', '.join(list_pydantic_model_names())}"
            ),
            "available_models": list_pydantic_model_names(),
        }
    return {
        "model_name": model_name,
        "json_schema": model_class.model_json_schema(),
        "fields": [
            {
                "name": field_name,
                "type": str(field_info.annotation) if hasattr(field_info, 'annotation') else "Any",
                "required": field_info.is_required(),
                "description": field_info.description or "",
            }
            for field_name, field_info in model_class.model_fields.items()
        ],
    }


# ---------------------------------------------------------------------------
# Helper: auto-import uuid at module load for default_factory lambdas
# ---------------------------------------------------------------------------
import uuid  # noqa: E402, F811
