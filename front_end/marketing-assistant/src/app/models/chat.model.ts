export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isLoading?: boolean;
}

export interface A2APart {
  text?: string;
  data?: unknown;
}

export interface A2AMessage {
  messageId: string;
  role: 'ROLE_USER' | 'ROLE_AGENT';
  contextId?: string;
  taskId?: string;
  parts: A2APart[];
}

export interface A2ATask {
  id: string;
  contextId: string;
  status?: { state: string; message?: A2AMessage };
  artifacts?: Array<{ artifactId?: string; name?: string; parts: A2APart[] }>;
}

export interface A2ASendMessageRequest {
  message: A2AMessage;
}

export interface A2AResponse {
  task?: A2ATask;
  message?: A2AMessage;
  error?: { code: number; message: string };
}
