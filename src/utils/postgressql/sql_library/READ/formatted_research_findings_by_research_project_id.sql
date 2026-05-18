SELECT * FROM "public"."formatted_research_findings"
WHERE research_project_id = $1
ORDER BY created_at DESC;