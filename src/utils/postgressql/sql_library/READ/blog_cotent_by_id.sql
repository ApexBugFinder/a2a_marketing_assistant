SELECT * FROM blog_content
WHERE id = $1
ORDER BY created_at DESC;