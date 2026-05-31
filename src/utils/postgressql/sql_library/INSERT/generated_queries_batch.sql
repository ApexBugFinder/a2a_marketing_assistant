INSERT INTO "public".generated_queries(
     id,
     research_project_id,
     generated_query,
     research_cycle_count,
     framework_category,
     status)
SELECT * FROM UNNEST(
     $1::UUID[],
     $2::UUID[],
     $3::TEXT[],
     $4::INTEGER[],
     $5::TEXT[],
     $6::TEXT[])
     AS t(
          id,
          research_project_id,
          generated_query,
          research_cycle_count,
          framework_category,
          status)
RETURNING *;