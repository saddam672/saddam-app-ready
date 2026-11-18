"use client";
import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import api from "@/lib/api";

export default function AuditLogPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const load = () => api.get("/admin/audit-logs?limit=300").then((r) => setLogs(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-2">
        <h1 className="text-2xl font-bold">Audit Log</h1>
        <button onClick={load} className="p-2 bg-surface border border-gray-600 rounded-lg"><RefreshCw size={16} /></button>
      </div>
      <p className="text-sm text-text-muted mb-6">Every sensitive admin action: who, what, before / after, reason and IP. Entries cannot be edited from the app.</p>
      <div className="bg-surface border border-gray-700 rounded-xl overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-background border-b border-gray-700 text-text-muted">
            <tr><th className="p-3">Time</th><th className="p-3">Admin</th><th className="p-3">Action</th><th className="p-3">Target</th><th className="p-3">Before &rarr; After</th><th className="p-3">Reason</th><th className="p-3">IP</th></tr>
          </thead>
          <tbody>
            {logs.length === 0 && <tr><td colSpan={7} className="p-8 text-center text-text-muted">No actions recorded yet.</td></tr>}
            {logs.map((l) => (
              <tr key={l.id} className="border-b border-gray-800 align-top">
                <td className="p-3 whitespace-nowrap">{new Date(l.created_at).toLocaleString()}</td>
                <td className="p-3">{l.admin_email}</td>
                <td className="p-3 font-semibold">{l.action}</td>
                <td className="p-3 font-mono">{l.target_type}{l.target_id ? ` ${String(l.target_id).slice(0, 8)}` : ""}</td>
                <td className="p-3 font-mono max-w-[260px] break-all">{l.before_value ? JSON.stringify(l.before_value) : "-"} &rarr; {l.after_value ? JSON.stringify(l.after_value) : "-"}</td>
                <td className="p-3">{l.reason || "-"}</td>
                <td className="p-3 font-mono">{l.ip_address}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
