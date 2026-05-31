INSERT INTO "public".linkedin_accounts (id, account_id, name, author_urn, email, access_token, token_expires_at)
VALUES ($1, $2, $3, $4, $5, $6, $7)
RETURNING *;