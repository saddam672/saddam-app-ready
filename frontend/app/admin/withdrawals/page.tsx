"use client";
import { useEffect, useState } from "react";
import { RefreshCw, Check, X } from "lucide-react";
import toast from "react-hot-toast";
import api from "@/lib/api";

interface Withdrawal {
  id: string; email: string; full_name: string; amount: number; status: string;
  destination?: string; source?: string; created_at: string;
}

export default function WithdrawalsPage() {
  const [rows, setRows] = useState<Withdrawal[]>([]);
  const [status, setStatus] = useState("PENDING");
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = async () => {
    try { setRows((await api.get(`/admin/withdrawals?status=${status}`)).data); }
    catch { toast.error("Failed to load withdrawals"); }
  };
  useEffect(() => { load(); }, [status]);

  const review = async (w: Withdrawal, approve: boolean) => {
    const note = prompt(approve
      ? `Payout sent to ${w.destination}.\nEnter the TXID / payment reference:`
      : "Reason for rejection (the amount will be returned to the user):");
    if (!note || !note.trim()) return;
    setBusyId(w.id);
    try {
      await api.put(`/admin/withdrawals/${w.id}/review`, { approve, note: note.trim() });
      toast.success(approve ? "Approved" : "Rejected and refunded to wallet");
      load();
    } catch (e: any) { toast.error(e.response?.data?.detail || "Failed"); }
    finally { setBusyId(null); }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Withdrawal Requests</h1>
        <div className="flex gap-2">
          {["PENDING", "SUCCESS", "REJECTED"].map((s) => (
            <button key={s} onClick={() => setStatus(s)} className={`px-3 py-1.5 rounded-lg text-xs border ${status === s ? "bg-primary border-primary text-white" : "border-gray-600 text-text-muted"}`}>{s}</button>
          ))}
          <button onClick={load} className="p-2 bg-surface border border-gray-600 rounded-lg"><RefreshCw size={16} /></button>
        </div>
      </div>
      <div className="bg-surface border border-gray-700 rounded-xl overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-background border-b border-gray-700 text-text-muted">
            <tr><th className="p-4">User</th><th className="p-4">Amount</th><th className="p-4">Pay to</th><th className="p-4">Requested</th><th className="p-4 text-right">Action</th></tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={5} className="p-8 text-center text-text-muted">Nothing here.</td></tr>}
            {rows.map((w) => (
              <tr key={w.id} className="border-b border-gray-800">
                <td className="p-4"><p className="font-medium">{w.full_name}</p><p className="text-xs text-text-muted">{w.email}</p></td>
                <td className="p-4 font-bold">${w.amount.toFixed(2)} <span className="text-[10px] text-text-muted">({w.source})</span></td>
                <td className="p-4 font-mono text-xs break-all max-w-[260px]">{w.destination}</td>
                <td className="p-4 text-xs">{new Date(w.created_at).toLocaleString()}</td>
                <td className="p-4 text-right whitespace-nowrap">
                  {w.status === "PENDING" ? (
                    <>
                      <button disabled={busyId === w.id} onClick={() => review(w, true)} className="px-3 py-1.5 mr-2 bg-success/20 text-success rounded text-xs inline-flex items-center gap-1"><Check size={14} /> Approve</button>
                      <button disabled={busyId === w.id} onClick={() => review(w, false)} className="px-3 py-1.5 bg-danger/20 text-danger rounded text-xs inline-flex items-center gap-1"><X size={14} /> Reject</button>
                    </>
                  ) : <span className="text-xs text-text-muted">{w.status}</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
