SELECT * FROM blog_content
WHERE research_project_id = $1
ORDER BY created_at DESC;