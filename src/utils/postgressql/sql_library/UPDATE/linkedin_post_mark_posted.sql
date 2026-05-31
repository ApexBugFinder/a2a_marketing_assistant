UPDATE "public"."linkedin_posts"
SET linkedin_post_id = $2,
    metadata = metadata || jsonb_build_object(
        'posted', true,
        'posted_at', CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT),
        'updated_at', CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT)
    )
WHERE id = $1
RETURNING *;
