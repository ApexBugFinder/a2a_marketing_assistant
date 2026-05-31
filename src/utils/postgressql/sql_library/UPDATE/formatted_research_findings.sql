UPDATE "public"."formatted_research_findings"
SET research_project_id       = $2,
    source                    = $3,
     title                     = $4,
     author                    = $5,
     relevance_to_research_topic = $6,
     publication_date          = $7,
     source_url                = $8,
     keywords_and_key_aspects  = $9,
     query                     = $10,
     research_cycle_count      = $11
WHERE id = $1
RETURNING *;
