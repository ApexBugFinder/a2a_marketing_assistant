INSERT INTO "public".research_projects (id, name, query, description, created_at, updated_at)
VALUES ($1, $2, $3, $4, $5, $6)
RETURNING *;
