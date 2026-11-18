"use client";
import { useState, useEffect } from "react";
import { Settings, Save } from "lucide-react";
import toast from "react-hot-toast";
import api from "@/lib/api";
import { Button } from "@/components/ui/Button";

export default function SpinSettingsPage() {
  const [prizes, setPrizes] = useState("0.001, 0.002, 0.005, 0.008, 0.01, 0.0, 0.003, 0.004");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/config/init").then(res => {
      // fetch from configs
      api.get("/admin/config").then(cfg => {
        // If endpoint exists
      }).catch(() => {});
    });
  }, []);

  const handleSave = async () => {
    setLoading(true);
    try {
      const prizeArray = prizes.split(",").map(p => parseFloat(p.trim())).filter(p => !isNaN(p));
      await api.put("/admin/spin-prizes", prizeArray);
      toast.success("Spin prizes updated!");
    } catch (e) { toast.error("Failed to update"); }
    finally { setLoading(false); }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 flex items-center gap-2"><Settings /> Spin Wheel Settings</h1>
      <div className="bg-surface border border-gray-700 p-6 rounded-xl">
        <label className="block text-sm text-text-muted mb-2">Spin Prizes (Comma separated values in $)</label>
        <textarea 
          className="w-full bg-background border border-gray-600 p-3 rounded-lg text-sm mb-4 h-24" 
          value={prizes} 
          onChange={e => setPrizes(e.target.value)} 
        />
        <Button onClick={handleSave} isLoading={loading} className="flex items-center gap-2">
          <Save size={16}/> Save Prizes
        </Button>
      </div>
    </div>
  );
}