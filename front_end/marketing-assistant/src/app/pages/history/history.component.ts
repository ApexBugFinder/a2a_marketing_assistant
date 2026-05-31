import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { DeliverableCardComponent } from '../../components/deliverable-card/deliverable-card.component';
import { DeliverablesService } from '../../services/deliverables.service';
import { BlogContent } from '../../models/blog-content.model';
import { LinkedInPost } from '../../models/linkedin-post.model';
import { ResearchProject } from '../../models/research-project.model';

type StatusFilter = 'all' | 'approved' | 'rejected' | 'posted';

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [
    FormsModule, MatTabsModule, MatIconModule,
    MatProgressBarModule, MatSelectModule, MatFormFieldModule,
    MatButtonToggleModule, DeliverableCardComponent,
  ],
  templateUrl: './history.component.html',
  styleUrl: './history.component.scss',
})
export class HistoryComponent implements OnInit {
  projects: ResearchProject[] = [];
  selectedProjectId = '';
  statusFilter: StatusFilter = 'all';

  allBlogPosts: BlogContent[] = [];
  allLinkedInPosts: LinkedInPost[] = [];
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
          this.loadHistory();
        }
      },
      error: () => this.snack.open('Could not load research projects', 'Dismiss', { duration: 4000 }),
    });
  }

  onProjectChange(): void { this.loadHistory(); }
  onFilterChange(): void {}

  get filteredBlogs(): BlogContent[] {
    return this.allBlogPosts.filter((p) => this.matchesFilter(p, 'blog'));
  }

  get filteredLinkedIn(): LinkedInPost[] {
    return this.allLinkedInPosts.filter((p) => this.matchesFilter(p, 'linkedin'));
  }

  private matchesFilter(item: BlogContent | LinkedInPost, type: 'blog' | 'linkedin'): boolean {
    if (this.statusFilter === 'all') return true;
    if (this.statusFilter === 'approved') return item.user_approved === true;
    if (this.statusFilter === 'rejected') return item.user_approved === false;
    if (this.statusFilter === 'posted') {
      if (type === 'linkedin') return (item as LinkedInPost).posted;
      if (type === 'blog') return (item as BlogContent).blog_status === 'published';
    }
    return true;
  }

  private loadHistory(): void {
    this.loading = true;
    const id = this.selectedProjectId || undefined;

    this.delivService.getBlogPosts(id).subscribe({
      next: (posts) => {
        this.allBlogPosts = posts;
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });

    this.delivService.getLinkedInPosts(id).subscribe({
      next: (posts) => (this.allLinkedInPosts = posts),
      error: () => {},
    });
  }
}
