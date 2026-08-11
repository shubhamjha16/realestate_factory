import React, { useState } from 'react';
import { integrationService } from '../services/integrationService';
import { WebhookDeliveryResult, WebhookVerifyResult } from '../types';

export const WebhookTester: React.FC = () => {
  const [url, setUrl] = useState<string>('https://bank-nbfc.sandbox.com/callbacks/valuation');
  const [secret, setSecret] = useState<string>('whsec_bank_super_secret_key');
  const [simulateFailures, setSimulateFailures] = useState<number>(0);
  const [deliveryResult, setDeliveryResult] = useState<WebhookDeliveryResult | null>(null);
  const [verifyResult, setVerifyResult] = useState<WebhookVerifyResult | null>(null);
  const [tamperedBody, setTamperedBody] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  const handleDeliver = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const res = await integrationService.deliverWebhook(url, secret, { job_id: 'job_123', status: 'completed' }, simulateFailures);
      setDeliveryResult(res);
      setTamperedBody(JSON.stringify({ job_id: 'job_123', status: 'completed' }, null, 2));
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (tampered: boolean) => {
    if (!deliveryResult) return;
    try {
      setLoading(true);
      const bodyToTest = tampered ? tamperedBody + ' ' : tamperedBody; // Add 1 character tamper
      const res = await integrationService.verifyWebhook(secret, deliveryResult.timestamp, bodyToTest, deliveryResult.signature);
      setVerifyResult(res);
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-950 text-slate-100 p-6 rounded-2xl border border-slate-800 space-y-6">
      <div className="border-b border-slate-800 pb-4">
        <h3 className="text-lg font-bold text-white">Bank LOS Webhook Integration & HMAC Tester</h3>
        <p className="text-xs text-slate-400">
          HMAC-SHA256 raw body signature verification and exponential backoff dead-letter tester.
        </p>
      </div>

      <form onSubmit={handleDeliver} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="block text-xs text-slate-400 mb-1">Target Endpoint</label>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs font-mono text-slate-200"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">HMAC Secret Key</label>
          <input
            type="text"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs font-mono text-slate-200"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Simulate Delivery Failures</label>
          <select
            value={simulateFailures}
            onChange={(e) => setSimulateFailures(Number(e.target.value))}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
          >
            <option value={0}>0 Failures (Delivered)</option>
            <option value={3}>3 Failures (Dead-Letter)</option>
          </select>
        </div>

        <div className="sm:col-span-3 flex justify-end">
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
          >
            {loading ? 'Processing...' : 'Send Signed Webhook Callback'}
          </button>
        </div>
      </form>

      {deliveryResult && (
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-4">
          <div className="flex justify-between items-center pb-2 border-b border-slate-800 text-xs">
            <span className="font-semibold text-slate-300">Delivery Status:</span>
            <span
              className={`px-2.5 py-0.5 text-[10px] font-bold uppercase rounded border ${
                deliveryResult.status === 'delivered'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-red-500/10 text-red-400 border-red-500/20'
              }`}
            >
              {deliveryResult.status}
            </span>
          </div>

          <div className="space-y-1 font-mono text-[11px]">
            <span className="text-slate-400 block">X-Signature-256 (HMAC-SHA256):</span>
            <span className="text-indigo-300 break-all">{deliveryResult.signature}</span>
          </div>

          {/* Attempts timeline */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-400">Delivery Attempts History:</span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
              {deliveryResult.attempts.map((att) => (
                <div key={att.attempt} className="p-2.5 bg-slate-950/60 border border-slate-800/80 rounded-lg space-y-1">
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="text-slate-400">Attempt {att.attempt}</span>
                    <span className={att.status === 'success' ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
                      HTTP {att.http_code}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 block font-mono">Backoff: {att.backoff_seconds}s</span>
                </div>
              ))}
            </div>
          </div>

          {/* Tamper testing buttons */}
          <div className="pt-2 border-t border-slate-800 flex gap-3">
            <button
              onClick={() => handleVerify(false)}
              className="py-1.5 px-3 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition"
            >
              Verify Valid Payload
            </button>
            <button
              onClick={() => handleVerify(true)}
              className="py-1.5 px-3 text-xs font-semibold bg-amber-600 hover:bg-amber-500 text-white rounded-lg transition"
            >
              Test 1-Char Tampered Body
            </button>
          </div>

          {verifyResult && (
            <div
              className={`p-3 rounded-lg border text-xs font-semibold flex justify-between items-center ${
                verifyResult.valid
                  ? 'bg-emerald-950/40 border-emerald-800/80 text-emerald-200'
                  : 'bg-red-950/40 border-red-800/80 text-red-200'
              }`}
            >
              <span>{verifyResult.message}</span>
              <span className="uppercase text-[10px] font-bold font-mono">
                {verifyResult.valid ? 'VERIFIED' : 'REJECTED (TAMPERED)'}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
