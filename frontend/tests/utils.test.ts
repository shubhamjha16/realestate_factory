import { describe, expect, it } from 'vitest';
import { compareMoney, formatLakhCrore, formatMoney } from '@/utils/money';
import {
  AmbiguousUnitError,
  UnverifiedFactorError,
  convertArea,
  isStateDependent,
  sqftPerUnit,
} from '@/utils/area';
import { redactOwnerName, redactSurveyNo, scrubForTelemetry } from '@/utils/redactDisplay';

describe('money', () => {
  it('formats a decimal string without going through float arithmetic', () => {
    expect(formatMoney('10650000.00')).toBe('₹1,06,50,000.00');
  });

  it('reads crore and lakh the way a valuer does', () => {
    expect(formatLakhCrore('10650000')).toBe('₹1.07 Cr');
    expect(formatLakhCrore('250000')).toBe('₹2.50 L');
    expect(formatLakhCrore('99999')).toBe('₹99,999');
    expect(formatLakhCrore('-10650000')).toBe('-₹1.07 Cr');
  });

  it('rounds half-up on the digits, not through a float', () => {
    // (10650000 / 1e7).toFixed(2) === '1.06'. The digits say 1.07.
    expect(formatLakhCrore('10650000')).toBe('₹1.07 Cr');
    expect(formatLakhCrore('999950')).toBe('₹10.00 L'); // carries across every 9
    expect(formatLakhCrore('123456789')).toBe('₹12.35 Cr');
  });

  it('orders by magnitude without losing paise', () => {
    expect(compareMoney('1000000.01', '1000000.02')).toBeLessThan(0);
    expect(compareMoney('999999.99', '1000000.00')).toBeLessThan(0);
  });
});

describe('area', () => {
  it('converts through the same table the engine reads', () => {
    expect(convertArea(1, 'acre', 'sqft')).toBe(43560);
    expect(convertArea(40, 'guntha', 'acre')).toBeCloseTo(1, 10);
    expect(convertArea(1, 'sqm', 'sqft')).toBeCloseTo(10.7639104167, 8);
    expect(convertArea(160, 'marla', 'acre')).toBeCloseTo(1, 10);
  });

  it('agrees with backend/app/utils/geo.py, factor for factor', () => {
    // Both read packages/units/units.json. These are the values asserted on the
    // Python side in tests/test_money_and_units.py.
    expect(sqftPerUnit('sqft')).toBe(1);
    expect(sqftPerUnit('sqyd')).toBe(9);
    expect(sqftPerUnit('acre')).toBe(43560);
    expect(sqftPerUnit('guntha')).toBe(1089);
    expect(sqftPerUnit('cent')).toBe(435.6);
    expect(sqftPerUnit('kanal')).toBe(5445);
    expect(sqftPerUnit('sqm')).toBe(10.763910416709722);
  });

  it('refuses a unit that has no single factor rather than guessing', () => {
    expect(isStateDependent('bigha')).toBe(true);
    expect(() => convertArea(1, 'bigha', 'sqft')).toThrow(AmbiguousUnitError);
  });

  it('refuses an unverified factor unless the caller opts in', () => {
    expect(() => sqftPerUnit('bigha', { state: 'UP' })).toThrow(UnverifiedFactorError);
    expect(sqftPerUnit('bigha', { state: 'UP', allowUnverified: true })).toBe(27000);
  });

  it('shows how far apart two states are, which is why the state is required', () => {
    const up = sqftPerUnit('bigha', { state: 'UP', allowUnverified: true });
    const wb = sqftPerUnit('bigha', { state: 'WB', allowUnverified: true });
    expect((up - wb) / wb).toBeGreaterThan(0.87);
  });

  it('rejects an unknown unit', () => {
    expect(() => convertArea(1, 'furlong', 'sqft')).toThrow(/Unknown area unit/);
  });
});

describe('redaction', () => {
  it('keeps owner names and survey numbers out of what is displayed or reported', () => {
    expect(redactSurveyNo('118/2A')).toBe('11••••');
    expect(redactOwnerName('Ashwin Kumar')).toBe('A••••• K••••');
    expect(scrubForTelemetry({ job_id: 'x', owner_name: 'A', lat: 1, survey_no: 'y' })).toEqual({
      job_id: 'x',
    });
  });
});
