INSERT INTO "public".marketing_images(
  id,
  research_project_id,
  image_url,
  tiny_url,
  description,
  size_bytes,
  img_dimensions,
  created_at,
  saved_to_s3_at
)
SELECT
  id,
  research_project_id,
  image_url,
  tiny_url,
  description,
  size_bytes,
  img_dimensions,
  created_at,
  saved_to_s3_at
FROM UNNEST(
  $1::UUID[],
  $2::UUID[],
  $3::TEXT[],
  $4::TEXT[],
  $5::TEXT[],
  $6::INTEGER[],
  $7::TEXT[],
  $8::TIMESTAMP[],
  $9::TIMESTAMP[]
) AS t(
  id UUID,
  research_project_id UUID,
  image_url TEXT,
  tiny_url TEXT,
  description TEXT,
  size_bytes INTEGER,
  img_dimensions TEXT,
  created_at TIMESTAMP,
  saved_to_s3_at TIMESTAMP
)
RETURNING *;
