"use client";
import { useEffect, useState } from "react";
import { Search, RefreshCw, X, Edit3, ShieldAlert, Key, RotateCcw } from "lucide-react";
import toast from "react-hot-toast";
import api from "@/lib/api";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

export default function UsersPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [transactions, setTransactions] = useState<any[]>([]);
  
  const [editReal, setEditReal] = useState("");
  const [editBonus, setEditBonus] = useState("");
  const [reason, setReason] = useState("");
  const [consents, setConsents] = useState<any[]>([]);
  const [editSpin, setEditSpin] = useState("");
  const [newPass, setNewPass] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchUsers = async () => {
    const res = await api.get("/admin/users");
    setUsers(res.data);
  };

  useEffect(() => { fetchUsers(); }, []);

  const openUserDetail = async (id: string) => {
    try {
      const [userRes, txRes, conRes] = await Promise.all([
        api.get(`/admin/users/${id}`),
        api.get(`/admin/users/${id}/transactions`),
        api.get(`/admin/users/${id}/consents`)
      ]);
      setSelectedUser(userRes.data);
      setTransactions(txRes.data);
      setConsents(conRes.data);
      setReason("");
      setEditReal(userRes.data.real_balance.toString());
      setEditBonus(userRes.data.bonus_balance.toString());
      setEditSpin(userRes.data.spin_balance.toString());
      setIsModalOpen(true);
    } catch { toast.error("Failed to load details"); }
  };

  const handleUpdateBalances = async () => {
    if (reason.trim().length < 5) return toast.error("Write a reason (min 5 characters). It is saved in the audit log.");
    setLoading(true);
    try {
      await api.put(`/admin/users/${selectedUser.id}/update-balances`, {
        real_balance: parseFloat(editReal), bonus_balance: parseFloat(editBonus), spin_balance: parseFloat(editSpin), reason: reason.trim()
      });
      toast.success("Balances updated and logged!");
      setSelectedUser({ ...selectedUser, real_balance: editReal, bonus_balance: editBonus, spin_balance: editSpin });
      setReason("");
      fetchUsers();
    } catch (e: any) { toast.error(e.response?.data?.detail?.[0]?.msg || e.response?.data?.detail || "Update failed"); } finally { setLoading(false); }
  };

  const handleFreeze = async () => {
    const why = prompt(selectedUser.is_frozen ? "Reason for unfreezing:" : "Reason for freezing (trading will also be switched off):");
    if (!why || why.trim().length < 3) return;
    await api.put(`/admin/users/${selectedUser.id}/freeze`, { reason: why.trim() });
    toast.success(selectedUser.is_frozen ? "User Unfrozen" : "User Frozen (Ghost Mode)");
    setSelectedUser({ ...selectedUser, is_frozen: !selectedUser.is_frozen });
    fetchUsers();
  };

  const handleResetPass = async () => {
    if (!newPass || newPass.length < 8) return toast.error("Min 8 chars required");
    const why = prompt("Reason for resetting this password:");
    if (!why || why.trim().length < 3) return;
    await api.put(`/admin/users/${selectedUser.id}/reset-password`, { new_password: newPass, reason: why.trim() });
    toast.success("Password reset successful");
    setNewPass("");
  };

  const handleRefund = async (txId: string) => {
    const why = prompt("Reason for this refund:");
    if (!why || why.trim().length < 3) return;
    try {
      await api.put(`/admin/transactions/${txId}/refund`, { reason: why.trim() });
      toast.success("Transaction Refunded!");
      openUserDetail(selectedUser.id);
    } catch (e: any) { toast.error(e.response?.data?.detail || "Refund failed"); }
  };

  const filtered = users.filter(u => u.full_name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">User Management</h1>
        <button onClick={fetchUsers} className="p-2 bg-surface border border-gray-600 rounded-lg"><RefreshCw size={16}/></button>
      </div>

      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" size={20} />
        <input type="text" placeholder="Search users..." value={search} onChange={e => setSearch(e.target.value)} className="w-full pl-10 pr-4 py-3 bg-surface border border-gray-600 rounded-lg text-sm" />
      </div>

      <div className="bg-surface border border-gray-700 rounded-xl overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-background border-b border-gray-700 text-text-muted">
            <tr><th className="p-4">User</th><th className="p-4">Status</th><th className="p-4">Joined</th><th className="p-4 text-right">Action</th></tr>
          </thead>
          <tbody>
            {filtered.map(user => (
              <tr key={user.id} className="border-b border-gray-800 hover:bg-background/50 cursor-pointer" onClick={() => openUserDetail(user.id)}>
                <td className="p-4">
                  <p className="font-medium">{user.full_name}</p>
                  <p className="text-xs text-text-muted">{user.email}</p>
                </td>
                <td className="p-4">
                  <span className={`text-xs px-2 py-1 rounded ${user.is_frozen ? "bg-gray-600" : user.is_active ? "bg-success/20 text-success" : "bg-danger/20 text-danger"}`}>
                    {user.is_frozen ? "Frozen" : user.is_active ? "Active" : "Banned"}
                  </span>
                </td>
                <td className="p-4 text-xs">{new Date(user.created_at).toLocaleDateString()}</td>
                <td className="p-4 text-right"><Edit3 size={16} className="inline text-primary"/></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* USER DETAILS MODAL */}
      {isModalOpen && selectedUser && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-surface border border-gray-700 rounded-2xl p-6 w-full max-w-2xl my-8">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">User Control Panel</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-text-muted hover:text-white"><X size={20}/></button>
            </div>
            
            <div className="space-y-6">
              <div className="flex flex-wrap items-center gap-4 bg-background p-4 rounded-lg border border-gray-700">
                <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center font-bold text-primary text-lg">{selectedUser.full_name.charAt(0)}</div>
                <div className="flex-1">
                  <p className="font-bold text-lg">{selectedUser.full_name}</p>
                  <p className="text-sm text-text-muted">{selectedUser.email}</p>
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleFreeze} variant={selectedUser.is_frozen ? "outline" : "danger"} className="!w-auto px-3 py-1.5 text-xs flex items-center gap-1"><ShieldAlert size={14}/> {selectedUser.is_frozen ? "Unfreeze" : "Freeze"}</Button>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <Input label="Real Balance ($)" type="number" value={editReal} onChange={(e) => setEditReal(e.target.value)} />
                <Input label="Bonus Balance ($)" type="number" value={editBonus} onChange={(e) => setEditBonus(e.target.value)} />
                <Input label="Spin Balance ($)" type="number" value={editSpin} onChange={(e) => setEditSpin(e.target.value)} />
              </div>
              <input type="text" placeholder="Reason for this change (required, saved in audit log)" value={reason} onChange={e => setReason(e.target.value)} className="w-full bg-background border border-gray-600 rounded-lg px-3 py-2 text-sm" />
              <Button onClick={handleUpdateBalances} isLoading={loading} className="!w-auto px-6"><Edit3 size={16} className="mr-2"/> Update Balances</Button>

              <div className="border-t border-gray-700 pt-4">
                <p className="text-sm font-bold mb-2">Consent &amp; Trading Permission</p>
                <div className="flex flex-wrap gap-2 mb-2 text-xs">
                  <span className={`px-2 py-1 rounded ${selectedUser.terms_version ? "bg-success/20 text-success" : "bg-danger/20 text-danger"}`}>Terms: {selectedUser.terms_version ? `accepted v${selectedUser.terms_version}` : "not accepted"}</span>
                  <span className={`px-2 py-1 rounded ${selectedUser.trading_consent ? "bg-success/20 text-success" : "bg-gray-600 text-gray-200"}`}>Trading: {selectedUser.trading_consent ? "ALLOWED by user" : "OFF"}</span>
                </div>
                <div className="space-y-1 max-h-28 overflow-y-auto">
                  {consents.map((c) => (
                    <p key={c.id} className="text-[11px] text-text-muted">{new Date(c.created_at).toLocaleString()} · {c.consent_type} {c.action} v{c.version} · {c.ip_address}</p>
                  ))}
                </div>
                <p className="text-[11px] text-text-muted mt-2">Admins cannot switch trading on for a user. Only the user can give permission.</p>
              </div>

              <div className="border-t border-gray-700 pt-4">
                <p className="text-sm font-bold mb-2">Manual Password Reset</p>
                <div className="flex gap-2">
                  <input type="text" placeholder="New Password" value={newPass} onChange={e => setNewPass(e.target.value)} className="flex-1 bg-background border border-gray-600 rounded-lg px-3 py-2 text-sm" />
                  <Button onClick={handleResetPass} variant="outline" className="!w-auto px-4"><Key size={16}/> Reset</Button>
                </div>
              </div>

              <div className="border-t border-gray-700 pt-4">
                <p className="text-sm font-bold mb-2">Recent Transactions</p>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {transactions.map(tx => (
                    <div key={tx.id} className="flex justify-between items-center bg-background p-2 rounded border border-gray-700 text-xs">
                      <div>
                        <p className="font-bold">{tx.transaction_type} - ${tx.amount}</p>
                        <p className="text-text-muted">{new Date(tx.created_at).toLocaleString()} | {tx.status}</p>
                      </div>
                      {tx.status === "SUCCESS" && (
                        <button onClick={() => handleRefund(tx.id)} className="px-2 py-1 bg-danger/20 text-danger rounded hover:bg-danger/30 flex items-center gap-1"><RotateCcw size={12}/> Refund</button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}