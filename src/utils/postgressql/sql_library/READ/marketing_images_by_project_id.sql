SELECT * FROM marketing_images
WHERE research_project_id = $1
ORDER BY created_at DESC;