INSERT INTO "public".marketing_images (id, research_project_id, image_url, tiny_url, description, size_bytes, img_dimensions, created_at, saved_to_s3_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
RETURNING *;