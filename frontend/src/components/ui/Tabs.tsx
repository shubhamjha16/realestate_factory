import type { ReactNode } from 'react';

export interface Tab {
  id: string;
  label: string;
  content: ReactNode;
}

interface Props {
  tabs: readonly Tab[];
  activeId: string;
  onSelect: (id: string) => void;
}

export function Tabs({ tabs, activeId, onSelect }: Props) {
  const active = tabs.find((t) => t.id === activeId) ?? tabs[0];
  return (
    <div>
      <div role="tablist" className="flex gap-1 border-b border-ink/10">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={tab.id === active?.id}
            onClick={() => onSelect(tab.id)}
            className={`px-4 py-2 text-sm ${tab.id === active?.id ? 'border-b-2 border-navy font-medium text-navy' : 'text-ink/70'}`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" className="pt-4">
        {active?.content}
      </div>
    </div>
  );
}
