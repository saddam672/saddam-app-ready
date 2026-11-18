"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  ShieldAlert,
  Filter,
} from "lucide-react";
import toast from "react-hot-toast";
import api from "@/lib/api";

interface Log {
  id: string;
  user_id: string | null;
  error_type: string | null;
  error_message: string | null;
  device_info: string | null;
  is_resolved: boolean;
  created_at: string;
}

export default function DiagnosticsPage() {
  const [logs, setLogs] = useState<Log[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "unresolved" | "resolved">(
    "unresolved"
  );
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const fetchLogs = async () => {
    try {
      const res = await api.get("/admin/diagnostics");
      setLogs(res.data);
    } catch (err) {
      toast.error("Failed to load logs");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const resolveLog = async (id: string) => {
    setResolvingId(id);
    try {
      await api.put(`/admin/diagnostics/${id}/resolve`);
      toast.success("Marked as resolved");
      setLogs((prev) =>
        prev.map((l) => (l.id === id ? { ...l, is_resolved: true } : l))
      );
    } catch (err) {
      toast.error("Failed to resolve log");
    } finally {
      setResolvingId(null);
    }
  };

  const filtered = logs.filter((l) => {
    if (filter === "resolved") return l.is_resolved;
    if (filter === "unresolved") return !l.is_resolved;
    return true;
  });

  const unresolvedCount = logs.filter((l) => !l.is_resolved).length;
  const resolvedCount = logs.filter((l) => l.is_resolved).length;

  return (
    <div className="max-w-6xl mx-auto">
      {/* ==========================================
          HEADER
      ========================================== */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ShieldAlert className="text-danger" size={28} />
            <h1 className="text-2xl md:text-3xl font-bold">
              System Diagnostics
            </h1>
          </div>
          <p className="text-text-muted text-sm">
            Monitor and fix system errors in real-time
          </p>
        </div>
        <button
          onClick={fetchLogs}
          className="p-2.5 bg-surface border border-gray-600 rounded-lg hover:border-primary transition self-start"
          title="Refresh"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {/* ==========================================
          STATS
      ========================================== */}
      <div className="grid grid-cols-2 gap-3 mb-6">
        <div
          className={`bg-surface rounded-xl p-4 border ${
            unresolvedCount > 0 ? "border-danger/30" : "border-gray-700"
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-text-muted">Unresolved</p>
            <AlertTriangle
              size={16}
              className={
                unresolvedCount > 0 ? "text-danger" : "text-text-muted"
              }
            />
          </div>
          <p
            className={`text-2xl font-bold ${
              unresolvedCount > 0 ? "text-danger" : "text-text-muted"
            }`}
          >
            {unresolvedCount}
          </p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-gray-700">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-text-muted">Resolved</p>
            <CheckCircle size={16} className="text-success" />
          </div>
          <p className="text-2xl font-bold text-success">{resolvedCount}</p>
        </div>
      </div>

      {/* ==========================================
          FILTERS
      ========================================== */}
      <div className="flex gap-2 mb-4 items-center">
        <Filter size={16} className="text-text-muted" />
        {(["all", "unresolved", "resolved"] as const).map((f) => {
          const count =
            f === "all"
              ? logs.length
              : f === "resolved"
              ? resolvedCount
              : unresolvedCount;
          return (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                filter === f
                  ? "bg-primary text-white"
                  : "bg-surface border border-gray-600 hover:border-primary text-text-muted"
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)} ({count})
            </button>
          );
        })}
      </div>

      {/* ==========================================
          LOGS LIST
      ========================================== */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-24 bg-surface border border-gray-700 rounded-xl animate-pulse"
            ></div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-surface border border-gray-700 rounded-xl p-12 text-center">
          <CheckCircle size={48} className="text-success mx-auto mb-3" />
          <p className="text-text-muted font-medium">
            No {filter} errors found
          </p>
          <p className="text-xs text-text-muted mt-1">
            {filter === "unresolved"
              ? "System is running smoothly 🎉"
              : "All errors have been fixed"}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((log) => {
            const isResolving = resolvingId === log.id;
            return (
              <div
                key={log.id}
                className={`bg-surface border rounded-xl p-4 transition ${
                  log.is_resolved
                    ? "border-gray-700 opacity-60"
                    : "border-danger/30"
                }`}
              >
                <div className="flex items-start justify-between gap-3 flex-wrap sm:flex-nowrap">
                  <div className="flex gap-3 flex-1 min-w-0">
                    <div
                      className={`p-2 rounded-lg h-fit flex-shrink-0 ${
                        log.is_resolved
                          ? "bg-success/20 text-success"
                          : "bg-danger/20 text-danger"
                      }`}
                    >
                      {log.is_resolved ? (
                        <CheckCircle size={16} />
                      ) : (
                        <AlertTriangle size={16} />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className="font-bold text-sm">
                          {log.error_type || "Unknown Error"}
                        </span>
                        <span className="text-[10px] text-text-muted">
                          {new Date(log.created_at).toLocaleString("en-US", {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                        {log.user_id && (
                          <span className="text-[10px] bg-primary/20 text-primary px-1.5 py-0.5 rounded">
                            User: {log.user_id.substring(0, 8)}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-text-muted font-mono break-all leading-relaxed">
                        {log.error_message}
                      </p>
                      {log.device_info && (
                        <p className="text-[10px] text-text-muted mt-1">
                          💻 {log.device_info}
                        </p>
                      )}
                    </div>
                  </div>
                  {!log.is_resolved && (
                    <button
                      onClick={() => resolveLog(log.id)}
                      disabled={isResolving}
                      className="px-3 py-1.5 bg-success/20 text-success text-xs font-medium rounded-lg hover:bg-success/30 transition disabled:opacity-50 flex items-center gap-1.5 flex-shrink-0"
                    >
                      {isResolving ? (
                        <>
                          <RefreshCw size={12} className="animate-spin" />{" "}
                          Resolving...
                        </>
                      ) : (
                        <>
                          <CheckCircle size={12} /> Mark Resolved
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}