UPDATE "public".generated_queries
SET research_project_id = $2,
    generated_query = $3,
    research_cycle_count = $4,
    framework_category = $5,
    status = $6,
    created_at = $7,
    updated_at = $8
WHERE id = $1
RETURNING *;
