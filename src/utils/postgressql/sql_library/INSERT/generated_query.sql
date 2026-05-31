INSERT INTO "public".generated_queries(id, research_project_id, generated_query, research_cycle_count, framework_category, status)
VALUES ($1, $2, $3, $4, $5, $6)
RETURNING *;
