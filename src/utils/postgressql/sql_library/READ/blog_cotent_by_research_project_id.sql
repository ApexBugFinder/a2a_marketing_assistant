SELECT * FROM "public".blog_content
WHERE research_project_id = $1
ORDER BY (metadata->>'created_at') DESC NULLS LAST;
