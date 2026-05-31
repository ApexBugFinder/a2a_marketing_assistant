SELECT * FROM "public".blog_content
ORDER BY (metadata->>'created_at') DESC NULLS LAST;
