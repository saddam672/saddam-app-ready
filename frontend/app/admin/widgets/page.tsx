"use client";
import { useEffect, useState } from "react";
import { LayoutTemplate, Save, Plus, Trash2, ArrowUp, ArrowDown, Eye, EyeOff } from "lucide-react";
import toast from "react-hot-toast";
import api from "@/lib/api";
import { Button } from "@/components/ui/Button";

export default function WidgetsPage() {
  const [layout, setLayout] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/user/dashboard-layout").then(res => setLayout(res.data)).catch(() => {});
  }, []);

  const handleSave = async () => {
    setLoading(true);
    try {
      await api.put("/admin/dashboard-layout", { layout });
      toast.success("Dashboard Layout saved successfully!");
    } catch { toast.error("Failed to save layout"); } finally { setLoading(false); }
  };

  const toggleActive = (index: number) => {
    const newLayout = [...layout];
    newLayout[index].active = !newLayout[index].active;
    setLayout(newLayout);
  };

  const updateTitle = (index: number, newTitle: string) => {
    const newLayout = [...layout];
    newLayout[index].title = newTitle;
    setLayout(newLayout);
  };

  const moveUp = (index: number) => {
    if (index === 0) return;
    const newLayout = [...layout];
    [newLayout[index - 1], newLayout[index]] = [newLayout[index], newLayout[index - 1]];
    setLayout(newLayout);
  };

  const moveDown = (index: number) => {
    if (index === layout.length - 1) return;
    const newLayout = [...layout];
    [newLayout[index + 1], newLayout[index]] = [newLayout[index], newLayout[index + 1]];
    setLayout(newLayout);
  };

  const removeSection = (index: number) => setLayout(layout.filter((_, i) => i !== index));

  const addSection = (type: string) => {
    setLayout([...layout, { id: `sec_${Date.now()}`, type, title: type === "WIDGET" ? "" : "New Section", active: true }]);
  };

  return (
    <div className="max-w-4xl mx-auto pb-20">
      <div className="flex items-center gap-3 mb-8">
        <LayoutTemplate className="text-primary" size={32} />
        <div>
          <h1 className="text-2xl font-bold">Dashboard Layout Builder</h1>
          <p className="text-text-muted text-sm">Toggle sections, change titles, and reorder user dashboard.</p>
        </div>
      </div>

      <div className="space-y-3 mb-8">
        {layout.map((sec, index) => (
          <div key={sec.id} className={`flex items-center gap-4 p-4 rounded-xl border transition ${sec.active ? "bg-surface border-gray-700" : "bg-background border-gray-800 opacity-60"}`}>
            <div className="flex flex-col gap-1">
              <button onClick={() => moveUp(index)} className="text-text-muted hover:text-white"><ArrowUp size={14}/></button>
              <button onClick={() => moveDown(index)} className="text-text-muted hover:text-white"><ArrowDown size={14}/></button>
            </div>
            <div className="flex-1">
              <p className="text-xs text-primary font-bold mb-1">{sec.type}</p>
              {sec.title !== undefined ? (
                <input type="text" value={sec.title} onChange={(e) => updateTitle(index, e.target.value)} className="w-full bg-background border border-gray-600 rounded px-2 py-1 text-sm font-bold" />
              ) : (
                <p className="text-sm font-bold text-white">{sec.widget_name}</p>
              )}
            </div>
            <div className="flex gap-2">
              <button onClick={() => toggleActive(index)} className={`p-2 rounded-lg ${sec.active ? "bg-success/20 text-success" : "bg-gray-700 text-text-muted"}`}>
                {sec.active ? <Eye size={16}/> : <EyeOff size={16}/>}
              </button>
              <button onClick={() => removeSection(index)} className="p-2 bg-danger/20 text-danger rounded-lg"><Trash2 size={16}/></button>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-surface border border-gray-700 p-4 rounded-xl mb-8 flex flex-wrap gap-2">
        <p className="w-full text-xs text-text-muted mb-2">Add New Section:</p>
        <Button onClick={() => addSection("HERO")} className="!w-auto px-3 py-1 text-xs">+ Hero Balance</Button>
        <Button onClick={() => addSection("MARKET")} className="!w-auto px-3 py-1 text-xs">+ Market</Button>
        <Button onClick={() => addSection("REFERRAL")} className="!w-auto px-3 py-1 text-xs">+ Referral</Button>
        <Button onClick={() => addSection("WIDGET")} className="!w-auto px-3 py-1 text-xs">+ Widget (Spin/Ticker)</Button>
      </div>

      <Button onClick={handleSave} isLoading={loading} className="w-full py-4 text-lg flex items-center justify-center gap-2">
        <Save size={20} /> Save Layout
      </Button>
    </div>
  );
}