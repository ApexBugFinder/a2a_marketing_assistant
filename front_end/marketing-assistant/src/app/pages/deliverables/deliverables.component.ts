import { Component, OnInit } from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { DeliverableCardComponent, FeedbackSubmit } from '../../components/deliverable-card/deliverable-card.component';
import { DeliverablesService } from '../../services/deliverables.service';
import { BlogContent } from '../../models/blog-content.model';
import { LinkedInPost } from '../../models/linkedin-post.model';
import { ResearchProject } from '../../models/research-project.model';

@Component({
  selector: 'app-deliverables',
  standalone: true,
  imports: [
    FormsModule, MatTabsModule, MatIconModule,
    MatProgressBarModule, MatSelectModule, MatFormFieldModule,
    DeliverableCardComponent,
  ],
  templateUrl: './deliverables.component.html',
  styleUrl: './deliverables.component.scss',
})
export class DeliverablesComponent implements OnInit {
  projects: ResearchProject[] = [];
  selectedProjectId = '';

  blogPosts: BlogContent[] = [];
  linkedInPosts: LinkedInPost[] = [];
  loading = false;

  constructor(
    private delivService: DeliverablesService,
    private snack: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.delivService.getResearchProjects().subscribe({
      next: (p) => {
        this.projects = p;
        if (p.length) {
          this.selectedProjectId = p[0].id;
          this.loadDeliverables();
        }
      },
      error: () => this.snack.open('Could not load research projects', 'Dismiss', { duration: 4000 }),
    });
  }

  onProjectChange(): void {
    this.loadDeliverables();
  }

  private loadDeliverables(): void {
    this.loading = true;
    const id = this.selectedProjectId || undefined;

    this.delivService.getBlogPosts(id).subscribe({
      next: (posts) => {
        this.blogPosts = posts.filter((p) => !p.user_approved);
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });

    this.delivService.getLinkedInPosts(id).subscribe({
      next: (posts) => (this.linkedInPosts = posts.filter((p) => !p.user_approved)),
      error: () => {},
    });
  }

  onFeedback(ev: FeedbackSubmit): void {
    if (ev.type === 'blog') {
      this.delivService
        .submitBlogFeedback({ blog_id: ev.id, user_feedback: ev.user_feedback, user_approved: ev.user_approved })
        .subscribe({
          next: () => {
            this.blogPosts = this.blogPosts.filter((p) => p.id !== ev.id);
            this.snack.open(ev.user_approved ? 'Blog post approved!' : 'Blog post rejected.', 'OK', { duration: 3000 });
          },
          error: () => this.snack.open('Failed to submit feedback', 'Dismiss', { duration: 4000 }),
        });
    } else {
      this.delivService
        .submitLinkedInFeedback({ post_id: ev.id, user_feedback: ev.user_feedback, user_approved: ev.user_approved })
        .subscribe({
          next: () => {
            this.linkedInPosts = this.linkedInPosts.filter((p) => p.id !== ev.id);
            this.snack.open(ev.user_approved ? 'LinkedIn post approved!' : 'LinkedIn post rejected.', 'OK', { duration: 3000 });
          },
          error: () => this.snack.open('Failed to submit feedback', 'Dismiss', { duration: 4000 }),
        });
    }
  }
}
