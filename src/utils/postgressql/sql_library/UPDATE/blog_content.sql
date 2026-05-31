UPDATE "public".blog_content
SET title = $2,
    content = $3,
    seo_keywords = $4,
    publication_date = $5,
    keywords_and_key_aspects = $6,
    metadata = metadata || CAST($7 AS JSONB)
WHERE id = $1
RETURNING *;
