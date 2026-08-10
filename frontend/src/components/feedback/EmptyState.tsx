import type { ReactNode } from 'react';

interface Props {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: Props) {
  return (
    <div className="rounded border border-dashed border-ink/20 p-8 text-center">
      <p className="font-medium text-navy">{title}</p>
      {description ? <p className="mt-1 text-sm text-ink/70">{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
