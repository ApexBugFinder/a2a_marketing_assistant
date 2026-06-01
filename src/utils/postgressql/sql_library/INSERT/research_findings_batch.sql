INSERT INTO public.research_findings(
    id,
    research_project_id,
    source,
    author,
    pub_date,
    title,
    url,
    research_cycle_count)
SELECT * FROM UNNEST(
    $1::UUID[],
    $2::UUID[],
    $3::TEXT[],
    $4::TEXT[],
    $5::TEXT[],
    $6::TEXT[],
    $7::TEXT[],
    $8::INTEGER[])
    AS t(
        id,
        research_project_id,
        source,
        author,
        pub_date,
        title,
        url,
        research_cycle_count)
RETURNING *;