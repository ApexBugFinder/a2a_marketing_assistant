UPDATE "public".marketing_images
SET image_url = $2, tiny_url = $3, description = $4, size_bytes = $5, img_dimensions = $6, saved_to_s3_at = $7, updated_at = CURRENT_TIMESTAMP
WHERE id = $1
RETURNING *;