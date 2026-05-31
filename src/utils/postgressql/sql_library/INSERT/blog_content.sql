INSERT INTO "public".blog_content (id, research_project_id, title, content, seo_keywords, publication_date, keywords_and_key_aspects, metadata)
VALUES ($1, $2, $3, $4, $5, $6, $7, CAST($8 AS JSONB))
RETURNING *;
