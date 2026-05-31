import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { BlogContent, BlogFeedback } from '../models/blog-content.model';
import { LinkedInPost, LinkedInFeedback } from '../models/linkedin-post.model';
import { ResearchProject } from '../models/research-project.model';

@Injectable({ providedIn: 'root' })
export class DeliverablesService {
  private readonly base = environment.toolsApiUrl;

  constructor(private http: HttpClient) {}

  getResearchProjects(): Observable<ResearchProject[]> {
    return this.http.get<ResearchProject[]>(`${this.base}/postgres/research_projects`);
  }

  getBlogPosts(researchProjectId?: string): Observable<BlogContent[]> {
    const url = researchProjectId
      ? `${this.base}/blog_writer/blog_content?research_project_id=${researchProjectId}`
      : `${this.base}/blog_writer/blog_content`;
    return this.http.get<BlogContent[]>(url);
  }

  getLinkedInPosts(researchProjectId?: string): Observable<LinkedInPost[]> {
    const url = researchProjectId
      ? `${this.base}/linkedin/posts?research_project_id=${researchProjectId}`
      : `${this.base}/linkedin/posts`;
    return this.http.get<LinkedInPost[]>(url);
  }

  submitBlogFeedback(feedback: BlogFeedback): Observable<unknown> {
    return this.http.post(`${this.base}/blog_writer/feedback`, feedback);
  }

  submitLinkedInFeedback(feedback: LinkedInFeedback): Observable<unknown> {
    return this.http.post(`${this.base}/linkedin/feedback`, feedback);
  }
}
