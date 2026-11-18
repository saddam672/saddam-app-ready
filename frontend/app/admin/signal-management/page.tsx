"use client";
import { useEffect, useState, useRef } from "react";
import { Zap, Plus, Trash2, TrendingUp, TrendingDown, RefreshCw, Search, Info, Play, BarChart3, Loader2, CheckCircle2, XCircle } from "lucide-react";
import toast from "react-hot-toast";
import api from "@/lib/api";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

interface Signal {
  id: string; pair: string; signal_type: "BUY" | "SELL"; entry_price: number | null; target_price: number | null; stop_loss: number | null;
  status: string; created_at: string; effectiveness_score?: number; candle_pattern?: string; chart_pattern?: string;
  support_level?: number; resistance_level?: number; entry_zone?: string; analysis_details?: string; current_price?: number; trailing_sl?: number; position_size?: number;
  regime?: string; rsi?: number; reason?: string; sl_percent?: number; tp_percent?: number; votes_buy?: number; votes_sell?: number; votes_hold?: number;
}

interface SymbolInfo { symbol: string; type: string; }
interface JobStatus { id: string; status: "pending" | "running" | "done" | "error"; pairs_total: number; pairs_scanned: number; signals_found: number; signals_created: number; last_completed: string; current_pair: string; error: string | null; }

export default function SignalManagementPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [filteredSymbols, setFilteredSymbols] = useState<SymbolInfo[]>([]);
  const [symbolSearch, setSymbolSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingSymbols, setIsLoadingSymbols] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  
  const [scanTf, setScanTf] = useState<"1h" | "2h" | "4h">("1h");
  const [maxCoins, setMaxCoins] = useState(500);
  const [job, setJob] = useState<JobStatus | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const [form, setForm] = useState({ pair: "BTCUSDT", type: "BUY" as "BUY" | "SELL", entry: "", target: "", stop: "" });

  const fetchSignals = async () => {
    try { const res = await api.get("/user/signals"); setSignals(res.data); } 
    catch { toast.error("Failed to load signals"); } finally { setIsLoading(false); }
  };

  const fetchSymbols = async () => {
    try {
      const res = await api.get("/admin/binance-symbols");
      setSymbols(res.data.symbols || []); setFilteredSymbols(res.data.symbols || []);
    } catch {
      const fallback = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"];
      setSymbols(fallback.map(s => ({ symbol: s, type: "FALLBACK" }))); setFilteredSymbols(fallback.map(s => ({ symbol: s, type: "FALLBACK" })));
    } finally { setIsLoadingSymbols(false); }
  };

  useEffect(() => { fetchSignals(); fetchSymbols(); }, []);
  useEffect(() => {
    if (!symbolSearch.trim()) setFilteredSymbols(symbols);
    else setFilteredSymbols(symbols.filter(s => s.symbol.includes(symbolSearch.toUpperCase())));
  }, [symbolSearch, symbols]);

  useEffect(() => { return () => { if (pollIntervalRef.current) clearInterval(pollIntervalRef.current); }; }, []);

  const handleRunGenerator = async () => {
    if (!confirm(`⚠️ Run generator?\n• TF: ${scanTf}\n• Coins: ${maxCoins}\nContinue?`)) return;
    try {
      toast.loading("Starting...", { id: "gen" });
      const res = await api.post("/admin/run-signal-generator", { timeframe: scanTf, max_coins: maxCoins });
      toast.success("Started!", { id: "gen" });
      setJob({ id: res.data.job_id, status: "pending", pairs_total: 0, pairs_scanned: 0, signals_found: 0, signals_created: 0, last_completed: "", current_pair: "Fetching...", error: null });
      
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = setInterval(async () => {
        try {
          const statusRes = await api.get(`/admin/generator-status/${res.data.job_id}`);
          setJob(statusRes.data);
          if (statusRes.data.status === "done") {
            clearInterval(pollIntervalRef.current!); toast.success("Done!"); fetchSignals(); setTimeout(() => setJob(null), 8000);
          } else if (statusRes.data.status === "error") { clearInterval(pollIntervalRef.current!); toast.error("Error"); }
        } catch { }
      }, 1500);
    } catch (err: any) { toast.error(err.response?.data?.detail || "Failed", { id: "gen" }); }
  };

  const handleAnalyze = async () => {
    setIsAnalyzing(true); toast.loading("Analyzing...", { id: "an" });
    try { const res = await api.post("/admin/analyze-signals"); toast.success(`Analyzed ${res.data.analyzed}`, { id: "an" }); fetchSignals(); } 
    catch { toast.error("Failed", { id: "an" }); } finally { setIsAnalyzing(false); }
  };

  const handleCreateSignal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.entry || !form.target || !form.stop) return toast.error("Fill all fields");
    setIsCreating(true);
    try {
      await api.post("/admin/signals", { pair: form.pair, signal_type: form.type, entry_price: parseFloat(form.entry), target_price: parseFloat(form.target), stop_loss: parseFloat(form.stop) });
      toast.success("Created!"); setForm({ ...form, entry: "", target: "", stop: "" }); fetchSignals();
    } catch { toast.error("Failed"); } finally { setIsCreating(false); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete?")) return; setDeletingId(id);
    try { await api.delete(`/admin/signals/${id}`); toast.success("Deleted"); setSignals(p => p.filter(s => s.id !== id)); } 
    catch { toast.error("Failed"); } finally { setDeletingId(null); }
  };

  const progressPercent = job && job.pairs_total > 0 ? Math.round((job.pairs_scanned / job.pairs_total) * 100) : 0;

  return (
    <div className="max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-8">
        <div><h1 className="text-2xl font-bold flex items-center gap-2"><Zap className="text-warning" /> Signal Engine</h1><p className="text-text-muted text-sm">{symbols.length} pairs available</p></div>
        <button onClick={fetchSignals} className="p-2.5 bg-surface border border-gray-600 rounded-lg"><RefreshCw size={16} /></button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* GENERATOR */}
        <div className="bg-gradient-to-br from-success/20 to-surface border border-success/30 rounded-xl p-5">
          <h3 className="font-bold flex items-center gap-2 mb-2"><Play className="text-success" size={20} /> Run Signal Generator</h3>
          <div className="flex gap-2 mb-4">
            <div className="flex-1"><label className="text-[10px] text-text-muted block mb-1">Timeframe</label><select value={scanTf} onChange={e => setScanTf(e.target.value as any)} className="w-full bg-background border border-gray-600 rounded p-1.5 text-xs"><option value="1h">1h</option><option value="2h">2h</option><option value="4h">4h</option></select></div>
            <div className="flex-1"><label className="text-[10px] text-text-muted block mb-1">Max Coins</label><select value={maxCoins} onChange={e => setMaxCoins(Number(e.target.value))} className="w-full bg-background border border-gray-600 rounded p-1.5 text-xs"><option value={100}>100</option><option value={200}>200</option><option value={500}>500</option></select></div>
          </div>
          <Button onClick={handleRunGenerator} disabled={job?.status === "running"} variant="success" className="!w-auto px-6"><Play size={16} className="mr-2"/> {job?.status === "running" ? "Running..." : "Run"}</Button>
        </div>
        {/* ANALYZER */}
        <div className="bg-gradient-to-br from-primary/20 to-surface border border-primary/30 rounded-xl p-5">
          <h3 className="font-bold flex items-center gap-2 mb-2"><BarChart3 className="text-primary" size={20} /> Analyze Signals</h3>
          <p className="text-xs text-text-muted mb-4">Score based on R/R, Patterns, & Entry Zones</p>
          <Button onClick={handleAnalyze} isLoading={isAnalyzing} className="!w-auto px-6"><BarChart3 size={16} className="mr-2"/> Analyze</Button>
        </div>
      </div>

      {/* PROGRESS */}
      {job && (
        <div className="bg-surface border border-warning/40 rounded-xl p-5 mb-6">
          <div className="flex justify-between items-center mb-2"><h3 className="font-bold flex items-center gap-2">{job.status === "running" ? <Loader2 className="animate-spin text-warning" size={16}/> : <CheckCircle2 className="text-success" size={16}/>} {job.status.toUpperCase()}</h3><span className="font-mono text-warning text-sm">{job.pairs_scanned} / {job.pairs_total}</span></div>
          <div className="bg-background rounded-full h-3 mb-3 overflow-hidden"><div className="bg-warning h-full transition-all duration-500" style={{ width: `${progressPercent}%` }} /></div>
          <div className="flex justify-between text-xs"><span>Found: {job.signals_found}</span><span>Saved: {job.signals_created}</span></div>
        </div>
      )}

      {/* CREATE FORM */}
      <form onSubmit={handleCreateSignal} className="bg-surface border border-gray-700 rounded-xl p-6 mb-6">
        <h2 className="text-lg font-bold mb-4">Create Manually</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-4">
          <div className="md:col-span-2"><label className="text-xs text-text-muted">Pair ({filteredSymbols.length})</label><div className="relative"><Search size={14} className="absolute left-2 top-3 text-text-muted"/><input type="text" placeholder="Search..." value={symbolSearch} onChange={e => setSymbolSearch(e.target.value)} className="w-full pl-7 py-2 mb-1 bg-background border border-gray-600 rounded text-xs"/></div><select value={form.pair} onChange={e => setForm({...form, pair: e.target.value})} className="w-full bg-background border border-gray-600 rounded p-2 text-sm">{filteredSymbols.map(s => <option key={s.symbol} value={s.symbol}>{s.symbol}</option>)}</select></div>
          <div><label className="text-xs text-text-muted">Type</label><select value={form.type} onChange={e => setForm({...form, type: e.target.value as any})} className="w-full bg-background border border-gray-600 rounded p-2 text-sm"><option value="BUY">BUY</option><option value="SELL">SELL</option></select></div>
          <Input label="Entry" type="number" step="0.00001" value={form.entry} onChange={e => setForm({...form, entry: e.target.value})} />
          <Input label="Target" type="number" step="0.00001" value={form.target} onChange={e => setForm({...form, target: e.target.value})} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-4"><Input label="Stop Loss" type="number" step="0.00001" value={form.stop} onChange={e => setForm({...form, stop: e.target.value})} /></div>
        <Button type="submit" isLoading={isCreating} className="!w-auto px-6"><Plus size={16} className="mr-2"/> Create</Button>
      </form>

      {/* SIGNALS LIST */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold">Active Signals ({signals.length})</h2>
        {isLoading ? <div className="animate-pulse h-40 bg-surface rounded-xl"/> : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {signals.map(s => {
              const isBuy = s.signal_type === "BUY";
              return (
                <div key={s.id} className="bg-surface border border-gray-700 rounded-xl p-4 flex flex-col gap-3">
                  <div className="flex justify-between border-b border-gray-700 pb-2">
                    <div><h3 className="font-bold text-lg text-white font-mono">{s.pair}</h3><p className="text-xs text-text-muted">Current: ${s.current_price || s.entry_price}</p></div>
                    <div className="flex items-center gap-2"><span className={`px-2 py-1 rounded text-xs font-bold ${isBuy ? "bg-success text-black" : "bg-danger text-white"}`}>{s.signal_type}</span><button onClick={() => handleDelete(s.id)} className="text-danger"><Trash2 size={14}/></button></div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-background p-2 rounded"><p className="text-text-muted">Entry</p><p className="font-mono text-white">${s.entry_price}</p></div>
                    <div className="bg-background p-2 rounded"><p className="text-text-muted">Size</p><p className="font-mono text-primary">{s.position_size?.toFixed(2)}x</p></div>
                    <div className="bg-danger/10 p-2 rounded"><p className="text-danger">SL ({s.sl_percent?.toFixed(2)}%)</p><p className="font-mono text-danger">${s.stop_loss}</p></div>
                    <div className="bg-success/10 p-2 rounded"><p className="text-success">TP ({s.tp_percent?.toFixed(2)}%)</p><p className="font-mono text-success">${s.target_price}</p></div>
                  </div>
                  <div className="flex justify-between text-[11px] text-center text-text-muted mt-1">
                    <div><p>Regime</p><p className="text-white">{s.regime || "-"}</p></div>
                    <div><p>RSI</p><p className="text-white">{s.rsi?.toFixed(1)}</p></div>
                    <div><p>Support</p><p className="text-success">{s.support_level?.toFixed(4)}</p></div>
                    <div><p>Resist</p><p className="text-danger">{s.resistance_level?.toFixed(4)}</p></div>
                  </div>
                  {s.analysis_details && (
                    <div className="mt-2 pt-2 border-t border-gray-700 text-[11px]">
                      <p className="text-text-muted">Pattern: <span className="text-white">{s.candle_pattern}</span></p>
                      <p className="text-text-muted">Trend: <span className="text-white">{s.chart_pattern}</span></p>
                      <div className="bg-primary/20 text-primary text-center p-1 mt-1 rounded font-bold">📍 {s.entry_zone}</div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}