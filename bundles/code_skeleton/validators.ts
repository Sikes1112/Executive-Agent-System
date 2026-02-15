// validators.ts (deterministic, no imports)

export type Severity = 'error' | 'warning' | 'info';

export type ValidationError = {
  code: string;
  field: string;
  severity: Severity;
  message: string;
};

const ERROR: Severity = 'error';
const WARNING: Severity = 'warning';
const INFO: Severity = 'info';

export function isNonEmptyString(s: any): boolean {
  return typeof s === 'string' && s.trim() !== '';
}

export function minLength(s: any, n: number): boolean {
  return typeof s === 'string' && s.length >= n;
}

export function isOneOf(v: any, allowed: readonly string[]): boolean {
  return allowed.indexOf(v) >= 0;
}

export function isStringArray(v: any): boolean {
  return Array.isArray(v) && v.every((x) => typeof x === 'string');
}

export function pushErr(out: ValidationError[], code: string, field: string, severity: Severity, message: string): void {
  out.push({ code, field, severity, message });
}

const VALID_SENTIMENT: readonly string[] = ["positive", "neutral", "negative"];
const VALID_TONE: readonly string[] = ["professional", "friendly", "apologetic", "firm"];
const VALID_DRAFT_STATUS: readonly string[] = ["draft", "edited", "final"];
const VALID_ACTION_STATUS: readonly string[] = ["OPEN", "IN_PROGRESS", "BLOCKED", "DONE", "CANCELED"];

export function validateReplyDraft(x: any): ValidationError[] {
  const e: ValidationError[] = [];
  if (!isNonEmptyString(x?.id)) pushErr(e, 'REPLYDRAFT_01', 'id', ERROR, 'ID must be a non-empty string.');
  if (!isNonEmptyString(x?.reviewId)) pushErr(e, 'REPLYDRAFT_02', 'reviewId', ERROR, 'Review ID must be a non-empty string.');
  if (!minLength(x?.text, 15)) pushErr(e, 'REPLYDRAFT_03', 'text', WARNING, 'Text must be at least 15 characters.');
  if (!isOneOf(x?.tone, VALID_TONE)) pushErr(e, 'REPLYDRAFT_04', 'tone', ERROR, 'Tone must be one of professional,friendly,apologetic,firm.');
  if (!isOneOf(x?.status, VALID_DRAFT_STATUS)) pushErr(e, 'REPLYDRAFT_05', 'status', WARNING, 'Status must be one of draft,edited,final.');
  return e;
}

export function validateActionItem(x: any): ValidationError[] {
  const e: ValidationError[] = [];
  if (!isNonEmptyString(x?.id)) pushErr(e, 'ACTIONITEM_01', 'id', ERROR, 'ID must be a non-empty string.');
  if (!isNonEmptyString(x?.reviewId)) pushErr(e, 'ACTIONITEM_02', 'reviewId', ERROR, 'Review ID must be a non-empty string.');
  if (!isNonEmptyString(x?.title)) pushErr(e, 'ACTIONITEM_03', 'title', ERROR, 'Title must be a non-empty string.');
  if (!isOneOf(x?.status, VALID_ACTION_STATUS)) pushErr(e, 'ACTIONITEM_04', 'status', ERROR, 'Status must be one of OPEN,IN_PROGRESS,BLOCKED,DONE,CANCELED.');
  if (x?.dueDate !== undefined && !isNonEmptyString(x?.dueDate)) pushErr(e, 'ACTIONITEM_05', 'dueDate', WARNING, 'Due date must be a non-empty string if present.');
  return e;
}

export function validateReview(x: any): ValidationError[] {
  const e: ValidationError[] = [];
  if (!isNonEmptyString(x?.id)) pushErr(e, 'REVIEW_01', 'id', ERROR, 'ID must be a non-empty string.');
  if (!minLength(x?.content, 10)) pushErr(e, 'REVIEW_02', 'content', WARNING, 'Content must be at least 10 characters.');
  if (!isOneOf(x?.sentiment, VALID_SENTIMENT)) pushErr(e, 'REVIEW_03', 'sentiment', ERROR, 'Sentiment must be one of positive,neutral,negative.');
  if (x?.issues !== undefined && !isStringArray(x?.issues)) pushErr(e, 'REVIEW_04', 'issues', WARNING, 'Issues must be a string array if present.');

  if (x?.replyDraft) {
    const rd = validateReplyDraft(x.replyDraft);
    for (let i = 0; i < rd.length; i++) e.push(rd[i]);
  }

  if (Array.isArray(x?.actionItems)) {
    for (let i = 0; i < x.actionItems.length; i++) {
      const ae = validateActionItem(x.actionItems[i]);
      for (let j = 0; j < ae.length; j++) {
        ae[j].field = 'actionItems[' + i + '].' + ae[j].field;
        e.push(ae[j]);
      }
    }
  }

  return e;
}
