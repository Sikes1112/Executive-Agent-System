// types.ts (deterministic, no imports)

export type Sentiment = 'positive' | 'neutral' | 'negative';

export type ReplyTone = 'professional' | 'friendly' | 'apologetic' | 'firm';

export type ReplyDraftStatus = 'draft' | 'edited' | 'final';

export type ActionStatus = 'OPEN' | 'IN_PROGRESS' | 'BLOCKED' | 'DONE' | 'CANCELED';

export type ThreadStatusEnum = 'NEW' | 'ANALYZED' | 'DRAFTED' | 'EDITED' | 'SENT' | 'RESOLVED' | 'ARCHIVED';

export interface Review {
  id: string;
  content: string;
  sentiment: Sentiment;
  issues?: string[];
  replyDraft?: ReplyDraft;
  actionItems?: ActionItem[];
}

export interface IssueTag {
  id: string;
  name: string;
  description?: string;
}

export interface ReplyDraft {
  id: string;
  reviewId: string;
  text: string;
  tone: ReplyTone;
  status: ReplyDraftStatus;
}

export interface ActionItem {
  id: string;
  reviewId: string;
  title: string;
  status: ActionStatus;
  dueDate?: string;
}

export interface ThreadStatus {
  id: string;
  reviewId: string;
  status: ThreadStatusEnum;
}
