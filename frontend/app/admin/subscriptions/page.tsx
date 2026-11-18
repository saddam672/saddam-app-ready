"use client";

import { useEffect, useState } from "react";
import {
  CreditCard,
  Search,
  Crown,
  TrendingUp,
  RefreshCw,
  Users,
} from "lucide-react";
import toast from "react-hot-toast";
import api from "@/lib/api";

interface Subscription {
  id: string;
  user_name: string;
  user_email: string;
  plan_name: string;
  is_active: boolean;
  start_date: string;
  end_date: string;
  amount_paid: number;
}

export default function AdminSubscriptionsPage() {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "active" | "expired">("all");

  const fetchSubscriptions = async () => {
    try {
      const res = await api.get("/admin/subscriptions");
      setSubscriptions(res.data);
    } catch (err) {
      toast.error("Failed to load subscriptions");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSubscriptions();
  }, []);

  const filtered = subscriptions.filter((s) => {
    const matchesSearch =
      s.user_name?.toLowerCase().includes(search.toLowerCase()) ||
      s.user_email?.toLowerCase().includes(search.toLowerCase()) ||
      s.plan_name?.toLowerCase().includes(search.toLowerCase());

    const matchesFilter =
      filter === "all" ||
      (filter === "active" && s.is_active) ||
      (filter === "expired" && !s.is_active);

    return matchesSearch && matchesFilter;
  });

  const totalRevenue = subscriptions.reduce(
    (sum, s) => sum + (s.amount_paid || 0),
    0
  );
  const activeRevenue = subscriptions
    .filter((s) => s.is_active)
    .reduce((sum, s) => sum + (s.amount_paid || 0), 0);
  const activeCount = subscriptions.filter((s) => s.is_active).length;

  return (
    <div className="max-w-6xl mx-auto">
      {/* ==========================================
          HEADER
      ========================================== */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <CreditCard className="text-primary" size={28} />
            <h1 className="text-2xl md:text-3xl font-bold">Subscriptions</h1>
          </div>
          <p className="text-text-muted text-sm">
            Manage all user subscriptions and track revenue
          </p>
        </div>
        <button
          onClick={fetchSubscriptions}
          className="p-2.5 bg-surface border border-gray-600 rounded-lg hover:border-primary transition self-start"
          title="Refresh"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {/* ==========================================
          STATS CARDS
      ========================================== */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-gradient-to-br from-primary/20 to-surface border border-primary/30 rounded-xl p-5">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-text-muted uppercase tracking-wide">
              Total Revenue
            </p>
            <TrendingUp className="text-primary" size={18} />
          </div>
          <p className="text-3xl font-bold text-primary">
            ${totalRevenue.toFixed(2)}
          </p>
          <p className="text-xs text-text-muted mt-1">All time</p>
        </div>

        <div className="bg-surface border border-success/30 rounded-xl p-5">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-text-muted uppercase tracking-wide">
              Active Revenue
            </p>
            <Crown className="text-success" size={18} />
          </div>
          <p className="text-3xl font-bold text-success">
            ${activeRevenue.toFixed(2)}
          </p>
          <p className="text-xs text-text-muted mt-1">
            {activeCount} active subs
          </p>
        </div>

        <div className="bg-surface border border-gray-700 rounded-xl p-5">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-text-muted uppercase tracking-wide">
              Total Subscriptions
            </p>
            <Users className="text-text-muted" size={18} />
          </div>
          <p className="text-3xl font-bold">{subscriptions.length}</p>
          <p className="text-xs text-text-muted mt-1">All time</p>
        </div>
      </div>

      {/* ==========================================
          SEARCH + FILTERS
      ========================================== */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search
            className="absolute left-3 top-1/2 transform -translate-y-1/2 text-text-muted"
            size={20}
          />
          <input
            type="text"
            placeholder="Search by user or plan..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-surface border border-gray-600 rounded-lg focus:ring-2 focus:ring-primary outline-none text-sm"
          />
        </div>
        <div className="flex gap-2">
          {(["all", "active", "expired"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition whitespace-nowrap ${
                filter === f
                  ? "bg-primary text-white"
                  : "bg-surface border border-gray-600 hover:border-primary"
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* ==========================================
          TABLE
      ========================================== */}
      <div className="bg-surface border border-gray-700 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="p-6 space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-14 bg-background rounded-lg animate-pulse"
              ></div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <CreditCard
              size={40}
              className="text-text-muted mx-auto mb-3"
            />
            <p className="text-text-muted text-sm">
              {search || filter !== "all"
                ? "No subscriptions match your search"
                : "No subscriptions yet. Users will appear here after subscribing."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px]">
              <thead className="bg-background border-b border-gray-700">
                <tr className="text-left text-xs text-text-muted">
                  <th className="p-4">User</th>
                  <th className="p-4">Plan</th>
                  <th className="p-4">Amount</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Start</th>
                  <th className="p-4">End</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((sub) => (
                  <tr
                    key={sub.id}
                    className="border-b border-gray-800 hover:bg-background/50 transition"
                  >
                    <td className="p-4">
                      <div className="min-w-0">
                        <p className="font-medium text-sm truncate">
                          {sub.user_name}
                        </p>
                        <p className="text-xs text-text-muted truncate">
                          {sub.user_email}
                        </p>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="text-sm flex items-center gap-1.5 text-warning font-medium whitespace-nowrap">
                        <Crown size={14} /> {sub.plan_name}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className="text-sm font-bold text-success whitespace-nowrap">
                        ${sub.amount_paid.toFixed(2)}
                      </span>
                    </td>
                    <td className="p-4">
                      <span
                        className={`text-xs px-2 py-1 rounded whitespace-nowrap ${
                          sub.is_active
                            ? "bg-success/20 text-success"
                            : "bg-gray-700 text-text-muted"
                        }`}
                      >
                        {sub.is_active ? "Active" : "Expired"}
                      </span>
                    </td>
                    <td className="p-4 text-sm text-text-muted whitespace-nowrap">
                      {new Date(sub.start_date).toLocaleDateString("en-US", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </td>
                    <td className="p-4 text-sm text-text-muted whitespace-nowrap">
                      {new Date(sub.end_date).toLocaleDateString("en-US", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}