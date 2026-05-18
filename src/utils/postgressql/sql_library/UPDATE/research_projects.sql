UPDATE "public"."research_projects"
SET name=$2, description=$3, end_date=CURRENT_TIMESTAMP
WHERE id = $1;