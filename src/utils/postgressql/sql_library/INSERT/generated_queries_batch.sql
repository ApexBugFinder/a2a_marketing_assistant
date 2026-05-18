INSERT INTO "public".generated_queries(
     id,
     research_project_id,
     generated_query,
     research_cycle_count,
     created_at)
SELECT * FROM UNNEST(
     $1::UUID[],
     $2::UUID[],
     $3::TEXT[],
     $4::INTEGER[],
     $5::TIMESTAMP[])
     AS t(
          id,
          research_project_id,
          generated_query,
          research_cycle_count,
          created_at);