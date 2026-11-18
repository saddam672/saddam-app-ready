"use client";
import { useEffect, useState } from "react";
import { Plus, Trash2, Save } from "lucide-react";
import toast from "react-hot-toast";
import api from "@/lib/api";
import { Button } from "@/components/ui/Button";

interface Item { id: number; type: "alert" | "trend" | "news" | "update"; title: string; description?: string; time: string; link?: string; }

export default function AnnouncementsPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => { api.get("/user/announcements").then((r) => setItems(r.data || [])).catch(() => {}); }, []);

  const add = () => setItems([{ id: Date.now(), type: "update", title: "", description: "", time: "Just now" }, ...items]);
  const change = (id: number, patch: Partial<Item>) => setItems(items.map((i) => (i.id === id ? { ...i, ...patch } : i)));

  const save = async () => {
    if (items.some((i) => !i.title.trim())) return toast.error("Every announcement needs a title");
    setSaving(true);
    try {
      await api.put("/admin/config", { config_key: "ANNOUNCEMENTS", config_value: { items }, description: "Dashboard announcements" });
      toast.success("Announcements saved");
    } catch { toast.error("Save failed"); } finally { setSaving(false); }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex justify-between items-center mb-2">
        <h1 className="text-2xl font-bold">Announcements</h1>
        <button onClick={add} className="px-3 py-2 bg-primary text-white rounded-lg text-sm flex items-center gap-1"><Plus size={16} /> Add</button>
      </div>
      <p className="text-sm text-text-muted mb-6">Shown to users in the dashboard news box. Write only real, accurate information.</p>
      <div className="space-y-3 mb-6">
        {items.length === 0 && <p className="text-text-muted text-sm">No announcements yet.</p>}
        {items.map((i) => (
          <div key={i.id} className="bg-surface border border-gray-700 rounded-xl p-4 space-y-2">
            <div className="flex gap-2">
              <select value={i.type} onChange={(e) => change(i.id, { type: e.target.value as Item["type"] })} className="bg-background border border-gray-600 rounded-lg px-2 text-sm">
                <option value="update">Update</option><option value="news">News</option><option value="trend">Trend</option><option value="alert">Alert</option>
              </select>
              <input value={i.title} onChange={(e) => change(i.id, { title: e.target.value })} placeholder="Title" className="flex-1 bg-background border border-gray-600 rounded-lg px-3 py-2 text-sm" />
              <button onClick={() => setItems(items.filter((x) => x.id !== i.id))} className="p-2 text-danger"><Trash2 size={16} /></button>
            </div>
            <textarea value={i.description || ""} onChange={(e) => change(i.id, { description: e.target.value })} placeholder="Details (optional)" rows={2} className="w-full bg-background border border-gray-600 rounded-lg px-3 py-2 text-sm" />
            <div className="flex gap-2">
              <input value={i.time} onChange={(e) => change(i.id, { time: e.target.value })} placeholder="Date label, e.g. 16 Nov" className="w-40 bg-background border border-gray-600 rounded-lg px-3 py-2 text-xs" />
              <input value={i.link || ""} onChange={(e) => change(i.id, { link: e.target.value })} placeholder="Link (optional)" className="flex-1 bg-background border border-gray-600 rounded-lg px-3 py-2 text-xs" />
            </div>
          </div>
        ))}
      </div>
      <Button onClick={save} isLoading={saving} className="!w-auto px-8 flex items-center gap-2"><Save size={16} /> Save</Button>
    </div>
  );
}
