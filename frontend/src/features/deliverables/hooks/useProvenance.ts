import { useState, useEffect } from 'react';
import { deliverableService } from '../services/deliverableService';
import { DeliverableProvenance } from '../types';

export function useProvenance(deliverableId: string | null) {
  const [provenance, setProvenance] = useState<DeliverableProvenance | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!deliverableId) {
      setProvenance(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    deliverableService
      .getProvenance(deliverableId)
      .then((data) => {
        if (isMounted) {
          setProvenance(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to load provenance chain');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [deliverableId]);

  return { provenance, loading, error };
}
