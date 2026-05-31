SELECT * FROM "public"."linkedin_posts"
WHERE author_urn = $1
ORDER BY created_at DESC;