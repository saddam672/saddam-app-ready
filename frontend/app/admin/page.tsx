"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Users, Zap, Activity, CreditCard, TrendingUp, AlertTriangle, ArrowRight, MessageSquare, ShieldAlert, Cpu } from "lucide-react";
import api from "@/lib/api";
import toast from "react-hot-toast";

export default function AdminOverviewPage() {
  const [stats, setStats] = useState({ users: 0, pendingWithdrawals: 0, signals: 0, logs: 0 });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [u, f, s, l] = await Promise.allSettled([
          api.get("/admin/users"), api.get("/admin/withdrawals?status=PENDING"),
          api.get("/user/signals"), api.get("/admin/diagnostics")
        ]);
        setStats({
          users: u.status === "fulfilled" ? u.value.data.length : 0,
          pendingWithdrawals: f.status === "fulfilled" ? f.value.data.length : 0,
          signals: s.status === "fulfilled" ? s.value.data.length : 0,
          logs: l.status === "fulfilled" ? l.value.data.filter((x:any) => !x.is_resolved).length : 0,
        });
      } catch (e) { toast.error("Failed to load stats"); }
      finally { setIsLoading(false); }
    };
    fetchStats();
  }, []);

  if (isLoading) return <div className="p-10 text-center text-danger animate-pulse">Loading System Stats...</div>;

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2"><ShieldAlert className="text-danger" size={28} /><h1 className="text-2xl md:text-3xl font-bold">Admin Overview</h1></div>
        <p className="text-text-muted text-sm">Manage all aspects of your trading platform</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard icon={<Users size={22} className="text-primary" />} title="Total Users" value={stats.users.toString()} color="primary" href="/admin/users" />
        <StatCard icon={<Zap size={22} className="text-warning" />} title="Pending Withdrawals" value={stats.pendingWithdrawals.toString()} color="warning" href="/admin/withdrawals" />
        <StatCard icon={<Cpu size={22} className="text-success" />} title="Active Signals" value={stats.signals.toString()} color="success" href="/admin/signal-management" />
        <StatCard icon={<AlertTriangle size={22} className="text-danger" />} title="System Logs" value={stats.logs.toString()} color="danger" href="/admin/diagnostics" />
      </div>

      {stats.logs > 0 && (
        <div className="bg-warning/10 border border-warning/30 rounded-xl p-4 mb-8 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <AlertTriangle className="text-warning" size={20} />
            <div><p className="font-semibold text-warning text-sm">{stats.logs} unresolved system errors</p></div>
          </div>
          <Link href="/admin/diagnostics" className="text-warning text-sm font-medium hover:underline flex items-center gap-1">View Logs <ArrowRight size={14} /></Link>
        </div>
      )}

      <div className="bg-surface border border-gray-700 rounded-xl p-6 mb-8">
        <h2 className="text-lg font-bold mb-4 flex items-center gap-2"><TrendingUp size={18} className="text-primary" /> Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <QuickAction href="/admin/users" icon={<Users size={18} />} label="Manage Users" />
          <QuickAction href="/admin/signal-management" icon={<Cpu size={18} />} label="Run Generator" />
          <QuickAction href="/admin/settings" icon={<ShieldAlert size={18} />} label="Global Settings" />
          <QuickAction href="/admin/support" icon={<MessageSquare size={18} />} label="Support Inbox" />
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, title, value, color, href }: any) {
  return (
    <Link href={href} className="bg-surface border border-gray-700 rounded-xl p-5 hover:border-primary/50 transition block">
      <div className={`w-10 h-10 rounded-lg bg-${color}/20 flex items-center justify-center mb-3`}>{icon}</div>
      <p className="text-text-muted text-xs mb-1">{title}</p>
      <p className="text-2xl font-bold">{value}</p>
    </Link>
  );
}

function QuickAction({ href, icon, label }: any) {
  return (
    <Link href={href} className="bg-background border border-gray-700 p-3 rounded-lg text-center hover:border-primary hover:text-primary transition flex flex-col items-center gap-2 group">
      <div className="text-text-muted group-hover:text-primary transition">{icon}</div>
      <span className="text-xs font-medium">{label}</span>
    </Link>
  );
}