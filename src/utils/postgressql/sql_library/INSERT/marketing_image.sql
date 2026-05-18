INSERT INTO "public".marketing_images (id, research_project_id, image_url, tiny_url, description, created_at)
VALUES ($1, $2, $3, $4, $5, NOW());