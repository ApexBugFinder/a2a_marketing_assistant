UPDATE public.generated_queries
SET status = 'searched',
    updated_at = EXTRACT(EPOCH FROM NOW())::BIGINT
WHERE id = ANY($1::UUID[])
RETURNING *;