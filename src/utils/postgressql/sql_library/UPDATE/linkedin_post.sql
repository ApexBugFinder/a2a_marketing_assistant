UPDATE "public"."linkedin_posts"
SET text = $2,
    hashtags = $3,
    image_url = $4,
    scheduled_time = $5,
    metadata = metadata || jsonb_build_object('updated_at', CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT))
WHERE id = $1
RETURNING *;
