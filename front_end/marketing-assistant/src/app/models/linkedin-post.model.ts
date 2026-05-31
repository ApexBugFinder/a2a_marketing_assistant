export interface LinkedInPost {
  id: string;
  author_urn: string;
  text: string;
  hashtags: string[];
  image_url?: string;
  linkedin_post_id?: string;
  scheduled_time?: number;
  posted: boolean;
  updated_at?: number;
  post_removed: boolean;
  post_removed_at?: number;
  recsearch_project_id?: string;
  created_at: string;
  ai_review_score?: number;
  ai_feedback?: string;
  user_feedback?: string;
  user_approved?: boolean;
  user_approved_at?: string;
}

export interface LinkedInFeedback {
  post_id: string;
  user_feedback: string;
  user_approved: boolean;
}
