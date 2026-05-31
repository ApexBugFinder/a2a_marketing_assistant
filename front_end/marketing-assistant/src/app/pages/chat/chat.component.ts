import { Component, ViewChild, ElementRef, AfterViewChecked, inject } from '@angular/core';
import { AsyncPipe, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ChatService } from '../../services/chat.service';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [
    AsyncPipe, DatePipe, FormsModule, MatFormFieldModule, MatInputModule,
    MatButtonModule, MatIconModule, MatTooltipModule, MatProgressSpinnerModule,
  ],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss',
})
export class ChatComponent implements AfterViewChecked {
  @ViewChild('messageList') private messageList!: ElementRef;

  private chatService = inject(ChatService);

  inputText = '';
  messages$ = this.chatService.messages$;
  loading$ = this.chatService.loading$;

  ngAfterViewChecked(): void {
    this.scrollToBottom();
  }

  send(): void {
    const text = this.inputText.trim();
    if (!text) return;
    this.inputText = '';
    this.chatService.sendMessage(text);
  }

  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.send();
    }
  }

  clearChat(): void {
    this.chatService.clearSession();
  }

  private scrollToBottom(): void {
    try {
      this.messageList.nativeElement.scrollTop =
        this.messageList.nativeElement.scrollHeight;
    } catch {}
  }
}
