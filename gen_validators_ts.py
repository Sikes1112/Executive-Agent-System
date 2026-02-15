#!/usr/bin/env python3
import json
from pathlib import Path

WS = Path.home() / ".openclaw" / "workspace-exec"
rules_path = WS / "bundles" / "domain" / "validation_rules.json"
out_path = WS / "bundles" / "code_skeleton" / "validators.ts"

obj = json.loads(rules_path.read_text(encoding="utf-8"))
enums = obj.get("enums", {})
rules = obj.get("rules", [])

# Helpers
def enum_values(rule: str):
    # enum(a,b,c) -> [a,b,c]
    inner = rule[len("enum("):-1]
    return [x.strip() for x in inner.split(",") if x.strip()]

def min_len(rule: str):
    # minlength(10) -> 10
    inner = rule[len("minlength("):-1]
    return int(inner.strip())

# Collect enum lists from rules when possible (fallback to enums dict)
sentiments = enums.get("Sentiment", ["positive","neutral","negative"])
tones = enums.get("ReplyTone", ["professional","friendly","apologetic","firm"])
draft_status = enums.get("ReplyDraftStatus", ["draft","edited","final"])
action_status = enums.get("ActionStatus", ["OPEN","IN_PROGRESS","BLOCKED","DONE","CANCELED"])

# Pull mins from rules (fallback defaults)
review_content_min = 10
reply_text_min = 15
for r in rules:
    if r.get("entity")=="Review" and r.get("field")=="content" and str(r.get("rule","")).startswith("minlength("):
        review_content_min = min_len(r["rule"])
    if r.get("entity")=="ReplyDraft" and r.get("field")=="text" and str(r.get("rule","")).startswith("minlength("):
        reply_text_min = min_len(r["rule"])

ts = f"""// validators.ts (deterministic, no imports)

export type Severity = 'error' | 'warning' | 'info';

export type ValidationError = {{
  code: string;
  field: string;
  severity: Severity;
  message: string;
}};

const ERROR: Severity = 'error';
const WARNING: Severity = 'warning';
const INFO: Severity = 'info';

export function isNonEmptyString(s: any): boolean {{
  return typeof s === 'string' && s.trim() !== '';
}}

export function minLength(s: any, n: number): boolean {{
  return typeof s === 'string' && s.length >= n;
}}

export function isOneOf(v: any, allowed: readonly string[]): boolean {{
  return allowed.indexOf(v) >= 0;
}}

export function isStringArray(v: any): boolean {{
  return Array.isArray(v) && v.every((x) => typeof x === 'string');
}}

export function pushErr(out: ValidationError[], code: string, field: string, severity: Severity, message: string): void {{
  out.push({{ code, field, severity, message }});
}}

const VALID_SENTIMENT: readonly string[] = {json.dumps(sentiments)};
const VALID_TONE: readonly string[] = {json.dumps(tones)};
const VALID_DRAFT_STATUS: readonly string[] = {json.dumps(draft_status)};
const VALID_ACTION_STATUS: readonly string[] = {json.dumps(action_status)};

export function validateReplyDraft(x: any): ValidationError[] {{
  const e: ValidationError[] = [];
  if (!isNonEmptyString(x?.id)) pushErr(e, 'REPLYDRAFT_01', 'id', ERROR, 'ID must be a non-empty string.');
  if (!isNonEmptyString(x?.reviewId)) pushErr(e, 'REPLYDRAFT_02', 'reviewId', ERROR, 'Review ID must be a non-empty string.');
  if (!minLength(x?.text, {reply_text_min})) pushErr(e, 'REPLYDRAFT_03', 'text', WARNING, 'Text must be at least {reply_text_min} characters.');
  if (!isOneOf(x?.tone, VALID_TONE)) pushErr(e, 'REPLYDRAFT_04', 'tone', ERROR, 'Tone must be one of {",".join(tones)}.');
  if (!isOneOf(x?.status, VALID_DRAFT_STATUS)) pushErr(e, 'REPLYDRAFT_05', 'status', WARNING, 'Status must be one of {",".join(draft_status)}.');
  return e;
}}

export function validateActionItem(x: any): ValidationError[] {{
  const e: ValidationError[] = [];
  if (!isNonEmptyString(x?.id)) pushErr(e, 'ACTIONITEM_01', 'id', ERROR, 'ID must be a non-empty string.');
  if (!isNonEmptyString(x?.reviewId)) pushErr(e, 'ACTIONITEM_02', 'reviewId', ERROR, 'Review ID must be a non-empty string.');
  if (!isNonEmptyString(x?.title)) pushErr(e, 'ACTIONITEM_03', 'title', ERROR, 'Title must be a non-empty string.');
  if (!isOneOf(x?.status, VALID_ACTION_STATUS)) pushErr(e, 'ACTIONITEM_04', 'status', ERROR, 'Status must be one of {",".join(action_status)}.');
  if (x?.dueDate !== undefined && !isNonEmptyString(x?.dueDate)) pushErr(e, 'ACTIONITEM_05', 'dueDate', WARNING, 'Due date must be a non-empty string if present.');
  return e;
}}

export function validateReview(x: any): ValidationError[] {{
  const e: ValidationError[] = [];
  if (!isNonEmptyString(x?.id)) pushErr(e, 'REVIEW_01', 'id', ERROR, 'ID must be a non-empty string.');
  if (!minLength(x?.content, {review_content_min})) pushErr(e, 'REVIEW_02', 'content', WARNING, 'Content must be at least {review_content_min} characters.');
  if (!isOneOf(x?.sentiment, VALID_SENTIMENT)) pushErr(e, 'REVIEW_03', 'sentiment', ERROR, 'Sentiment must be one of {",".join(sentiments)}.');
  if (x?.issues !== undefined && !isStringArray(x?.issues)) pushErr(e, 'REVIEW_04', 'issues', WARNING, 'Issues must be a string array if present.');

  if (x?.replyDraft) {{
    const rd = validateReplyDraft(x.replyDraft);
    for (let i = 0; i < rd.length; i++) e.push(rd[i]);
  }}

  if (Array.isArray(x?.actionItems)) {{
    for (let i = 0; i < x.actionItems.length; i++) {{
      const ae = validateActionItem(x.actionItems[i]);
      for (let j = 0; j < ae.length; j++) {{
        ae[j].field = 'actionItems[' + i + '].' + ae[j].field;
        e.push(ae[j]);
      }}
    }}
  }}

  return e;
}}
"""

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(ts, encoding="utf-8")
print(f"WROTE {out_path}")
