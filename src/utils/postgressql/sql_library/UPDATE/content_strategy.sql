UPDATE "public".content_strategy
SET content_strategy = $1,
          content_strategy_overview = $2,
          key_messages= $3,
          target_audience = $4,
          content_formats_and_channels = $5,
          content_strategy_calendar = $6,
          updated_at = CURRENT_TIMESTAMP
WHERE id = $7
RETURNING *;