import type { Comparable, Point } from './types';

/**
 * Comparables are a map problem before they are a table problem, which is why
 * this lives in shared components rather than inside one feature — five
 * features render it.
 *
 * MapLibre lands in S7 and is lazy-loaded from `features/comparables/` only: it
 * is the heaviest dependency in the bundle (S21). S1 fixes the contract.
 */
export interface MapViewProps {
  centre: Point;
  radiusM: number;
  subject: Point | null;
  comparables: readonly Comparable[];
  selectedId?: string;
  onSelect?: (comparableId: string) => void;
}

export function MapView({ comparables, radiusM }: MapViewProps) {
  return (
    <div
      role="img"
      aria-label={`${comparables.length} comparables within ${radiusM} m`}
      className="grid h-64 place-items-center rounded border border-dashed border-ink/20 bg-mist text-sm text-ink/60"
    >
      Map view — MapLibre, lazy-loaded (S7)
    </div>
  );
}
