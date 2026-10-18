export type ActivityKind = 'import' | 'index' | 'question' | 'task' | 'approval' | 'test';

export type WorkspaceActivity = {
  id: string;
  kind: ActivityKind;
  repoId?: number;
  repoName?: string;
  title: string;
  detail?: string;
  timestamp: number;
  runId?: number;
  status?: string;
};

const KEY = 'github-ai-help:activity';

export function readActivities(): WorkspaceActivity[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function recordActivity(activity: Omit<WorkspaceActivity, 'id' | 'timestamp'>): WorkspaceActivity {
  const entry: WorkspaceActivity = {
    ...activity,
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: Date.now(),
  };
  const next = [entry, ...readActivities()].slice(0, 30);
  localStorage.setItem(KEY, JSON.stringify(next));
  window.dispatchEvent(new Event('workspace-activity'));
  return entry;
}

export function updateRunActivity(runId: number, patch: Partial<WorkspaceActivity>) {
  const next = readActivities().map(item => item.runId === runId ? {...item, ...patch} : item);
  localStorage.setItem(KEY, JSON.stringify(next));
  window.dispatchEvent(new Event('workspace-activity'));
}

export function formatRelativeTime(timestamp: number) {
  const seconds = Math.max(1, Math.floor((Date.now() - timestamp) / 1000));
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
