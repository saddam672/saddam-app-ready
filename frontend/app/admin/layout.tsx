"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard, Users, Zap, Settings, LogOut, Menu, X, ArrowLeft, 
  CreditCard, Building2, TrendingUp, MessageSquare, ShieldAlert, Loader2, Gift, Layers, Cpu
} from "lucide-react";
import { useStore } from "@/store/useStore";
import toast from "react-hot-toast";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAdmin, logout, isAuthenticated } = useStore();

  useEffect(() => {
    if (typeof window === "undefined") return;
    const timer = setTimeout(() => {
      if (!isAuthenticated || !isAdmin) {
        toast.error("Access Denied. Admin only.");
        router.push("/dashboard");
      } else {
        setIsChecking(false);
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [isAuthenticated, isAdmin, router]);

  const handleLogout = () => {
    logout();
    document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    router.push("/login");
  };

  // আপনার ৭টি সেকশন অনুযায়ী মেনু
  const navItems = [
    { name: "Overview", href: "/admin", icon: <LayoutDashboard size={18} /> }, // ১. Overview
    { name: "Users", href: "/admin/users", icon: <Users size={18} /> }, // ২. Users
    { name: "Airdrops", href: "/admin/airdrops", icon: <Gift size={18} /> }, // ৩. Airdrops
    { name: "Withdrawals", href: "/admin/withdrawals", icon: <CreditCard size={18} /> },
    { name: "Announcements", href: "/admin/announcements", icon: <TrendingUp size={18} /> },
    { name: "Audit Log", href: "/admin/audit-logs", icon: <ShieldAlert size={18} /> },
    { name: "Widgets & CMS", href: "/admin/widgets", icon: <Layers size={18} /> }, // ৫. Widgets
    { name: "Signal Engine", href: "/admin/signal-management", icon: <Cpu size={18} /> }, // ৬. Signal Engine
    { name: "Setup (company & fees)", href: "/setup", icon: <Building2 size={18} /> },
    { name: "Global Settings", href: "/admin/settings", icon: <Settings size={18} /> }, // ৭. Global Settings
    { name: "Subscriptions", href: "/admin/subscriptions", icon: <CreditCard size={18} /> },
    { name: "Support Chat", href: "/admin/support", icon: <MessageSquare size={18} /> },
    { name: "Diagnostics", href: "/admin/diagnostics", icon: <ShieldAlert size={18} /> },
  ];

  if (isChecking) return <div className="min-h-screen flex items-center justify-center bg-background"><Loader2 size={40} className="text-danger animate-spin" /></div>;
  if (!isAdmin) return null;

  return (
    <div className="min-h-screen bg-background flex flex-col md:flex-row">
      <div className="md:hidden flex items-center justify-between p-4 bg-surface border-b border-danger/30 sticky top-0 z-40">
        <div className="flex items-center gap-2"><ShieldAlert size={20} className="text-danger" /><span className="text-lg font-bold text-danger">Admin</span></div>
        <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="text-text-main p-2">{isSidebarOpen ? <X size={24} /> : <Menu size={24} />}</button>
      </div>

      <aside className={`fixed md:sticky top-0 inset-y-0 left-0 z-50 md:z-10 w-64 h-screen bg-surface border-r border-danger/20 transform transition-transform duration-300 ease-in-out ${isSidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"} flex flex-col`}>
        <div className="hidden md:flex items-center justify-center h-16 border-b border-danger/20 bg-danger/5">
          <span className="text-lg font-bold text-danger flex items-center gap-2"><ShieldAlert size={22} /> Admin Control</span>
        </div>
        <div className="p-3 border-b border-gray-700">
          <Link href="/dashboard" className="flex items-center gap-2 text-xs text-text-muted hover:text-white transition px-3 py-2 rounded-lg hover:bg-background"><ArrowLeft size={14} /> Back to User App</Link>
        </div>
        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => (
            <Link key={item.name} href={item.href} onClick={() => setIsSidebarOpen(false)} className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition text-sm ${pathname === item.href || (item.href !== "/admin" && pathname.startsWith(item.href)) ? "bg-danger/20 text-danger font-semibold" : "text-text-muted hover:bg-background hover:text-white"}`}>
              {item.icon}{item.name}
            </Link>
          ))}
        </nav>
        <div className="p-3 border-t border-gray-700">
          <div className="flex items-center gap-3 mb-3 px-1">
            <div className="w-9 h-9 rounded-full bg-danger/20 flex items-center justify-center text-danger font-bold flex-shrink-0 text-sm">{user?.full_name?.charAt(0)?.toUpperCase() || "A"}</div>
            <div className="overflow-hidden min-w-0">
              <p className="font-medium text-sm truncate">{user?.full_name || "Admin"}</p>
              <p className="text-[10px] text-danger truncate">Administrator</p>
            </div>
          </div>
          <button onClick={handleLogout} className="flex items-center gap-2 text-sm text-danger hover:text-red-400 transition w-full px-2 py-2 rounded-lg hover:bg-danger/10"><LogOut size={16} /> Logout</button>
        </div>
      </aside>

      {isSidebarOpen && <div onClick={() => setIsSidebarOpen(false)} className="fixed inset-0 bg-black/50 z-40 md:hidden"></div>}
      <main className="flex-1 p-4 md:p-8 overflow-x-hidden min-h-screen">{children}</main>
    </div>
  );
}