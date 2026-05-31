SELECT * FROM "public"."linkedin_posts"
WHERE (metadata->>'posted') IS DISTINCT FROM 'true'
AND (metadata->>'post_removed') IS DISTINCT FROM 'true'
ORDER BY scheduled_time ASC NULLS LAST;
