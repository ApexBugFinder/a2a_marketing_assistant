UPDATE "public"."linkedin_accounts"
SET access_token=$2, token_expires_at=$3, updated_at=CURRENT_TIMESTAMP
WHERE account_id = $1
RETURNING *;