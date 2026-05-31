INSERT INTO "public".linkedin_posts (id, author_urn, text, hashtags, image_url, scheduled_time, research_project_id, metadata)
VALUES ($1, $2, $3, $4, $5, $6, $7, CAST($8 AS JSONB))
RETURNING *;
