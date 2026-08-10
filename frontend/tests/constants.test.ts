import { describe, expect, it } from 'vitest';
import {
  ALL_JOB_TYPES,
  AGREEMENT_TYPES,
  COMPLIANCE_TYPES,
  PATH_BY_JOB_TYPE,
  RECONCILIATION_TYPES,
  VALUATION_TYPES,
  JOB_TYPE_LABELS,
} from '@/shared/constants/jobTypes';

/**
 * These mirror backend/app/configs/jobTypes.py by hand at S1. From S3 the
 * generated api-types make drift a build failure; until then this is the guard.
 */
describe('job types mirror the engine', () => {
  it('holds sixteen types across four paths', () => {
    expect(VALUATION_TYPES).toHaveLength(3);
    expect(COMPLIANCE_TYPES).toHaveLength(5);
    expect(AGREEMENT_TYPES).toHaveLength(6);
    expect(RECONCILIATION_TYPES).toHaveLength(2);
    expect(ALL_JOB_TYPES).toHaveLength(16);
    expect(new Set(ALL_JOB_TYPES).size).toBe(16);
  });

  it('routes every type to exactly one path', () => {
    for (const t of ALL_JOB_TYPES) {
      expect(PATH_BY_JOB_TYPE[t]).toBeDefined();
    }
    expect(new Set(Object.values(PATH_BY_JOB_TYPE))).toEqual(
      new Set(['valuation', 'compliance', 'agreement', 'reconciliation']),
    );
  });

  it('labels every type', () => {
    for (const t of ALL_JOB_TYPES) {
      expect(JOB_TYPE_LABELS[t]).toBeTruthy();
    }
  });
});
