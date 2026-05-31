UPDATE "public"."linkedin_accounts"
SET name=$2, author_urn=$3, email=$4, updated_at=CURRENT_TIMESTAMP
WHERE id = $1
RETURNING *;