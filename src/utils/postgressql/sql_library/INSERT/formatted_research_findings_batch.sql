INSERT INTO "public".formatted_research_findings(
  id,
  research_project_id,
  title,
  author,
  publication_date,
  source,
  finding_summary,
  relevance_to_research_topic,
  source_url,
  keywords_and_key_aspects,
  research_cycle_count,
  query
)
SELECT
  id,
  research_project_id,
  title,
  author,
  publication_date,
  source,
  finding_summary,
  relevance_to_research_topic,
  source_url,
  keywords_and_key_aspects,
  research_cycle_count,
  query
FROM UNNEST(
  $1::UUID[],
  $2::UUID[],
  $3::TEXT[],
  $4::TEXT[],
  $5::DATE[],
  $6::TEXT[],
  $7::TEXT[],
  $8::TEXT[],
  $9::TEXT[],
  $10::TEXT[],
  $11::INTEGER[],
  $12::TEXT[]
) AS t(
  id UUID,
  research_project_id UUID,
  title TEXT,
  author TEXT,
  publication_date DATE,
  source TEXT,
  finding_summary TEXT,
  relevance_to_research_topic TEXT,
  source_url TEXT,
  keywords_and_key_aspects TEXT,
  research_cycle_count INTEGER,
  query TEXT
)
RETURNING *;
