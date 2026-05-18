UPDATE "public".marketing_images
SET image_url = $2, tiny_url = $3, description = $4, updated_at = CURRENT_TIMESTAMP
WHERE id = $1;