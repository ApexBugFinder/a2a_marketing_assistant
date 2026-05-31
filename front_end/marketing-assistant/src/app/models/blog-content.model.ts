export interface BlogContent {
  id: string;
  research_project_id: string;
  title: string;
  content: string;
  seo_keywords?: string;
  blog_status?: string;
  publication_date?: string;
  blog_url?: string;
  keywords_and_key_aspects?: string;
  created_at: string;
  updated_at: string;
  ai_review_score?: number;
  ai_feedback?: string;
  user_feedback?: string;
  user_approved?: boolean;
  user_approved_at?: string;
}

export interface BlogFeedback {
  blog_id: string;
  user_feedback: string;
  user_approved: boolean;
}
