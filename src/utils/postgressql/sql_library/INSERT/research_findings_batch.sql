INSERT INTO public.research_findings(
    id,
    research_project_id,
    source,
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
    $7::INTEGER[])
    AS t(
        id,
        research_project_id,
        source,
        pub_date,
        title,
        url,
        research_cycle_count)
RETURNING *;