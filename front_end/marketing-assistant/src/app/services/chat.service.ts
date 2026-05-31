import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { environment } from '../../environments/environment';
import { A2ASendMessageRequest, ChatMessage } from '../models/chat.model';
import { v4 as uuidv4 } from 'uuid';

// A2A SSE event shapes after proto3 JSON (MessageToDict → camelCase field names)
interface A2AStatusUpdate {
  taskId?: string;
  contextId?: string;
  status?: {
    state?: string;                        // e.g. "TASK_STATE_INPUT_REQUIRED"
    message?: { parts?: Array<{ text?: string }> };
  };
  final?: boolean;
}

interface A2AArtifactUpdate {
  taskId?: string;
  contextId?: string;
  artifact?: {
    name?: string;
    parts?: Array<{ text?: string; data?: unknown }>;
  };
  lastChunk?: boolean;
}

interface A2AStreamEvent {
  statusUpdate?: A2AStatusUpdate;
  artifactUpdate?: A2AArtifactUpdate;
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly streamUrl = `${environment.agentApiUrl}/message:stream`;
  private contextId = uuidv4();

  private _messages = new BehaviorSubject<ChatMessage[]>([]);
  messages$ = this._messages.asObservable();

  private _loading = new BehaviorSubject<boolean>(false);
  loading$ = this._loading.asObservable();

  sendMessage(text: string): void {
    const userMsg: ChatMessage = {
      id: uuidv4(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    };
    const loadingMsg: ChatMessage = {
      id: 'loading',
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    };

    this._messages.next([...this._messages.value, userMsg, loadingMsg]);
    this._loading.next(true);

    const body: A2ASendMessageRequest = {
      message: {
        messageId: uuidv4(),
        role: 'ROLE_USER',
        contextId: this.contextId,
        parts: [{ text }],
      },
    };

    this.streamResponse(body);
  }

  private async streamResponse(body: A2ASendMessageRequest): Promise<void> {
    let abortController: AbortController | null = new AbortController();
    const timeoutId = setTimeout(() => abortController?.abort(), 600_000);

    try {
      const response = await fetch(this.streamUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'A2A-Version': '1.0' },
        body: JSON.stringify(body),
        signal: abortController.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let lastArtifactContent: string | null = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data:')) continue;
          const raw = line.slice(5).trim();
          if (!raw) continue;

          let event: A2AStreamEvent;
          try { event = JSON.parse(raw) as A2AStreamEvent; } catch { continue; }

          // ── Status update ───────────────────────────────────────────────
          const su = event.statusUpdate;
          if (su) {
            const state = su.status?.state ?? '';

            if (state.includes('INPUT_REQUIRED')) {
              const text = su.status?.message?.parts?.[0]?.text
                ?? 'Please provide more information.';
              this._loading.next(false);
              this.replaceLoading(text);
              clearTimeout(timeoutId);
              abortController = null;
              return;
            }
          }

          // ── Artifact update ──────────────────────────────────────────────
          const au = event.artifactUpdate;
          if (au?.artifact) {
            const parts = au.artifact.parts ?? [];
            const content = parts
              .map((p) =>
                p.text
                  ? p.text
                  : p.data != null
                  ? JSON.stringify(p.data, null, 2)
                  : ''
              )
              .join('');
            if (content) lastArtifactContent = content;

            if (au.lastChunk && lastArtifactContent) {
              this._loading.next(false);
              this.replaceLoading(lastArtifactContent);
              clearTimeout(timeoutId);
              abortController = null;
              return;
            }
          }
        }
      }

      this._loading.next(false);
      this.replaceLoading(lastArtifactContent ?? 'No response received.');
    } catch (err: any) {
      this._loading.next(false);
      const isAbort = err?.name === 'AbortError';
      const message = isAbort
        ? 'The agent is taking longer than expected. Please try again.'
        : (err?.message ?? 'Request failed');
      this.replaceLoading(`Error: ${message}`);
    } finally {
      clearTimeout(timeoutId);
      abortController = null;
    }
  }

  private replaceLoading(content: string): void {
    const current = this._messages.value.filter((m) => m.id !== 'loading');
    this._messages.next([
      ...current,
      { id: uuidv4(), role: 'assistant', content, timestamp: new Date() },
    ]);
  }

  clearSession(): void {
    this.contextId = uuidv4();
    this._messages.next([]);
  }
}