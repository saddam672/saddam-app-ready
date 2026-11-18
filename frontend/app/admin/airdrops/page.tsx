"use client";
import { useState, useEffect } from "react";
import { Gift, Plus, Trash2, Video, Link as LinkIcon } from "lucide-react";
import toast from "react-hot-toast";
import api from "@/lib/api";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

export default function AirdropsPage() {
  const [airdrops, setAirdrops] = useState<any[]>([]);
  const [form, setForm] = useState({ title: "", description: "", link_url: "", video_url: "" });
  const [loading, setLoading] = useState(false);

  const fetchAirdrops = async () => {
    const res = await api.get("/admin/airdrops");
    setAirdrops(res.data);
  };

  useEffect(() => { fetchAirdrops(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title || !form.link_url) return toast.error("Title and Link are required");
    setLoading(true);
    try {
      await api.post("/admin/airdrops", form);
      toast.success("Airdrop added!");
      setForm({ title: "", description: "", link_url: "", video_url: "" });
      fetchAirdrops();
    } catch { toast.error("Failed to add airdrop"); } finally { setLoading(false); }
  };

  const handleDelete = async (id: string) => {
    if(!confirm("Delete this airdrop?")) return;
    await api.delete(`/admin/airdrops/${id}`);
    toast.success("Deleted");
    fetchAirdrops();
  };

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 flex items-center gap-2"><Gift className="text-primary"/> Airdrop Manager</h1>
      
      <form onSubmit={handleCreate} className="bg-surface border border-gray-700 p-6 rounded-xl mb-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input label="Airdrop Title" value={form.title} onChange={e => setForm({...form, title: e.target.value})} required />
          <Input label="Link URL (Where to claim)" value={form.link_url} onChange={e => setForm({...form, link_url: e.target.value})} required />
          <Input label="Video URL (Optional)" value={form.video_url} onChange={e => setForm({...form, video_url: e.target.value})} />
        </div>
        <div>
          <label className="text-xs text-text-muted mb-1 block">Description</label>
          <textarea className="w-full bg-background border border-gray-600 p-3 rounded-lg text-sm h-20" value={form.description} onChange={e => setForm({...form, description: e.target.value})} />
        </div>
        <Button type="submit" isLoading={loading} className="!w-auto px-6"><Plus size={16} className="mr-2"/> Add Airdrop</Button>
      </form>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {airdrops.map(a => (
          <div key={a.id} className="bg-surface border border-gray-700 p-5 rounded-xl relative group">
            <button onClick={() => handleDelete(a.id)} className="absolute top-3 right-3 p-2 bg-danger/10 text-danger rounded-lg opacity-0 group-hover:opacity-100 transition"><Trash2 size={16}/></button>
            <h3 className="font-bold text-lg text-white mb-1">{a.title}</h3>
            <p className="text-xs text-text-muted mb-4">{a.description}</p>
            <div className="flex gap-2">
              <a href={a.link_url} target="_blank" className="flex-1 py-2 bg-primary/20 text-primary text-xs font-bold rounded flex items-center justify-center gap-1 hover:bg-primary/30"><LinkIcon size={14}/> Join Link</a>
              {a.video_url && <a href={a.video_url} target="_blank" className="p-2 bg-surface border border-gray-600 rounded hover:text-white"><Video size={16}/></a>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}