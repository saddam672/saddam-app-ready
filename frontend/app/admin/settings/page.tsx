"use client";
import { useEffect, useState } from "react";
import { Settings, Save, Plus, Trash2, LayoutTemplate, Link as LinkIcon, Type, ShieldAlert, DollarSign, Gift } from "lucide-react";
import toast from "react-hot-toast";
import Link from "next/link";
import api from "@/lib/api";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

export default function AdminSettingsPage() {
  const [loading, setLoading] = useState(false);
  const [elements, setElements] = useState<any[]>([]);
  const [fees, setFees] = useState({ deposit: 0, withdraw: 1.5, trade: 0.1 });
  const [spin, setSpin] = useState("0.01, 0.005, 0.001, 0.0, 0.008");
  const [killSwitch, setKillSwitch] = useState(false);
  const [maintenance, setMaintenance] = useState(false);

  useEffect(() => {
    api.get("/user/custom-elements").then(res => setElements(res.data)).catch(() => {});
    api.get("/config/init").then(res => {
      const s = res.data.settings;
      setMaintenance(s.maintenance_mode || false);
    }).catch(() => {});
    api.get("/user/spin-prizes").then(res => setSpin(res.data.join(", "))).catch(() => {});
  }, []);

  const handleSave = async () => {
    setLoading(true);
    try {
      await api.put("/admin/config", { config_key: "CUSTOM_ELEMENTS", config_value: elements });
      const prizesArr = spin.split(",").map((p:any) => parseFloat(p.trim())).filter((p:any) => !isNaN(p));
      await api.put("/admin/config", { config_key: "SPIN_PRIZES", config_value: prizesArr });
      await api.put("/admin/config", { config_key: "MAINTENANCE_MODE", config_value: { status: maintenance } });
      await api.put("/admin/config", { config_key: "GLOBAL_KILL_SWITCH", config_value: { active: killSwitch } });
      toast.success("Settings saved!");
    } catch { toast.error("Failed"); } finally { setLoading(false); }
  };

  const addElement = (type: "BUTTON" | "TEXT" | "LINK") => {
    setElements([...elements, { id: `el_${Date.now()}`, type, label: `New ${type}`, url: "", content: "", color: "primary" }]);
  };

  const updateElement = (index: number, field: string, value: string) => {
    const newEl = [...elements]; newEl[index][field] = value; setElements(newEl);
  };

  const removeElement = (index: number) => setElements(elements.filter((_, i) => i !== index));

  return (
    <div className="max-w-5xl mx-auto pb-20">
      <div className="flex items-center gap-3 mb-8"><Settings className="text-primary" size={32} /><div><h1 className="text-2xl font-bold">Global Settings & CMS</h1></div></div>

      <div className="space-y-6">
        {/* EMERGENCY CONTROLS */}
        <div className="bg-surface border border-danger/30 rounded-xl p-6">
          <h2 className="font-bold flex items-center gap-2 mb-4 text-danger"><ShieldAlert size={18}/> Emergency Controls</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-3 bg-background rounded-lg border border-gray-700">
              <div><p className="font-bold text-sm">Maintenance Mode</p><p className="text-xs text-text-muted">Block all users</p></div>
              <button onClick={() => setMaintenance(!maintenance)} className={`w-12 h-6 rounded-full ${maintenance ? "bg-danger" : "bg-gray-600"}`}><div className={`w-5 h-5 rounded-full bg-white transition-transform ${maintenance ? "translate-x-6" : "translate-x-0.5"}`} /></button>
            </div>
            <div className="flex items-center justify-between p-3 bg-background rounded-lg border border-gray-700">
              <div><p className="font-bold text-sm text-danger">Global Kill Switch</p><p className="text-xs text-text-muted">Pause all trades</p></div>
              <button onClick={() => setKillSwitch(!killSwitch)} className={`w-12 h-6 rounded-full ${killSwitch ? "bg-danger" : "bg-gray-600"}`}><div className={`w-5 h-5 rounded-full bg-white transition-transform ${killSwitch ? "translate-x-6" : "translate-x-0.5"}`} /></button>
            </div>
          </div>
        </div>

        {/* DYNAMIC UI BUILDER */}
        <div className="bg-surface border border-gray-700 rounded-xl p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-bold flex items-center gap-2"><LayoutTemplate size={18} className="text-primary"/> Dynamic UI Builder</h2>
            <div className="flex gap-2">
              <button onClick={() => addElement("BUTTON")} className="px-3 py-1.5 bg-primary/20 text-primary rounded text-xs font-bold flex items-center gap-1 hover:bg-primary/30"><Plus size={14}/> Add Button</button>
              <button onClick={() => addElement("TEXT")} className="px-3 py-1.5 bg-warning/20 text-warning rounded text-xs font-bold flex items-center gap-1 hover:bg-warning/30"><Type size={14}/> Add Text</button>
            </div>
          </div>
          <div className="space-y-3">
            {elements.map((el, i) => (
              <div key={el.id} className="bg-background p-4 rounded-lg border border-gray-700 flex flex-col md:flex-row gap-3 items-end">
                <div className="flex-1 w-full"><Input label="Label" value={el.label} onChange={(e) => updateElement(i, "label", e.target.value)} /></div>
                <div className="flex-1 w-full"><Input label="URL (Optional)" value={el.url} onChange={(e) => updateElement(i, "url", e.target.value)} /></div>
                <div className="w-full md:w-32"><Input label="Color" value={el.color} onChange={(e) => updateElement(i, "color", e.target.value)} /></div>
                <button onClick={() => removeElement(i)} className="p-3 text-danger bg-danger/10 rounded-lg hover:bg-danger/20 mb-0.5"><Trash2 size={16}/></button>
              </div>
            ))}
          </div>
        </div>

        {/* FINANCIAL & SPIN */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-surface border border-gray-700 rounded-xl p-6 space-y-4">
            <h2 className="font-bold flex items-center gap-2"><DollarSign size={18} className="text-success"/> Fees &amp; Limits</h2>
            <p className="text-sm text-text-muted">Deposit/withdrawal limits, withdrawal fee, payout time and refund rules now live in one place so the Terms, wallet and server rules always agree.</p>
            <Link href="/setup" className="inline-block px-4 py-2 rounded-lg bg-primary/20 text-primary text-sm font-semibold hover:bg-primary/30">Open Setup (company &amp; fees) &rarr;</Link>
          </div>
          <div className="bg-surface border border-gray-700 rounded-xl p-6">
            <h2 className="font-bold flex items-center gap-2 mb-4"><Gift size={18} className="text-warning"/> Spin Wheel Prizes</h2>
            <textarea className="w-full bg-background border border-gray-600 p-3 rounded-lg text-sm h-20" value={spin} onChange={(e) => setSpin(e.target.value)} />
          </div>
        </div>

        <Button onClick={handleSave} isLoading={loading} className="w-full py-4 text-lg flex items-center justify-center gap-2"><Save size={20} /> Save All Global Settings</Button>
      </div>
    </div>
  );
}