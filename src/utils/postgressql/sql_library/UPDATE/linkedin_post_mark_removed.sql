UPDATE "public"."linkedin_posts"
SET metadata = metadata || jsonb_build_object(
        'post_removed', true,
        'post_removed_at', CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT),
        'updated_at', CAST(EXTRACT(EPOCH FROM NOW()) AS BIGINT)
    )
WHERE id = $1
RETURNING *;
