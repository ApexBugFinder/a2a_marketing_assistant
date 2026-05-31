import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatBadgeModule } from '@angular/material/badge';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { MatExpansionModule } from '@angular/material/expansion';
import { BlogContent } from '../../models/blog-content.model';
import { LinkedInPost } from '../../models/linkedin-post.model';

export interface FeedbackSubmit {
  id: string;
  type: 'blog' | 'linkedin';
  user_feedback: string;
  user_approved: boolean;
}

@Component({
  selector: 'app-deliverable-card',
  standalone: true,
  imports: [
    DatePipe, FormsModule, MatCardModule, MatButtonModule,
    MatFormFieldModule, MatInputModule, MatChipsModule, MatIconModule,
    MatBadgeModule, MatTooltipModule, MatDividerModule, MatExpansionModule,
  ],
  templateUrl: './deliverable-card.component.html',
  styleUrl: './deliverable-card.component.scss',
})
export class DeliverableCardComponent implements OnInit {
  @Input() item!: BlogContent | LinkedInPost;
  @Input() type!: 'blog' | 'linkedin';
  @Input() readonly = false;

  @Output() feedbackSubmitted = new EventEmitter<FeedbackSubmit>();

  feedbackText = '';
  submitting = false;

  ngOnInit(): void {
    if (this.item.user_feedback) this.feedbackText = this.item.user_feedback;
  }

  get asBlog(): BlogContent { return this.item as BlogContent; }
  get asLinkedIn(): LinkedInPost { return this.item as LinkedInPost; }

  get statusLabel(): string {
    if (this.type === 'blog') return (this.item as BlogContent).blog_status ?? 'draft';
    return (this.item as LinkedInPost).posted ? 'posted' : 'pending';
  }

  get statusClass(): string {
    const s = this.statusLabel.toLowerCase();
    if (s === 'posted' || s === 'published') return 'status-posted';
    if (s === 'approved') return 'status-approved';
    if (s === 'rejected') return 'status-rejected';
    return 'status-pending';
  }

  approve(): void {
    this.emit(true);
  }

  reject(): void {
    this.emit(false);
  }

  private emit(approved: boolean): void {
    this.submitting = true;
    this.feedbackSubmitted.emit({
      id: this.item.id,
      type: this.type,
      user_feedback: this.feedbackText,
      user_approved: approved,
    });
  }
}
