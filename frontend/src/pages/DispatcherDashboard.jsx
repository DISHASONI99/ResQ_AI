import { useState, useEffect } from 'react'
import {
    Radio, MapPin, Shield, AlertTriangle, CheckCircle, XCircle,
    Clock, Phone, MessageSquare, Activity, Search, Filter, Menu
} from 'lucide-react'

const DispatcherDashboard = () => {
    const [incidents, setIncidents] = useState([])
    const [selectedIncident, setSelectedIncident] = useState(null)
    const [filter, setFilter] = useState('pending_dispatch') // pending_dispatch, active, resolved
    const [wsStatus, setWsStatus] = useState('disconnected')

    // Fetch initial queue
    useEffect(() => {
        fetchIncidents()
    }, [])

    // WebSocket Connection
    useEffect(() => {
        const ws = new WebSocket('ws://localhost:8000/ws/incidents');

        ws.onopen = () => setWsStatus('connected');
        ws.onclose = () => setWsStatus('disconnected');

        ws.onmessage = (event) => {
            const update = JSON.parse(event.data);
            console.log("Dispatcher WS Update:", update);

            if (update.type === 'new_incident') {
                setIncidents(prev => [update.incident, ...prev]);
            } else if (update.type === 'status_change' || update.type === 'commander_assigned') {
                setIncidents(prev => prev.map(inc =>
                    inc.incident_id === update.incident_id ? { ...inc, ...update } : inc
                ));
                // Update selected incident if it's the one being modified
                if (selectedIncident?.incident_id === update.incident_id) {
                    setSelectedIncident(prev => ({ ...prev, ...update }));
                }
            }
        };

        return () => ws.close();
    }, [selectedIncident]);

    const fetchIncidents = async () => {
        try {
            const res = await fetch('/api/dispatcher/queue');
            if (!res.ok) throw new Error(`API Error: ${res.status}`);
            const data = await res.json();
            if (data.incidents && Array.isArray(data.incidents)) {
                setIncidents(data.incidents);
            } else if (Array.isArray(data)) {
                setIncidents(data);
            } else {
                console.error("Dispatcher queue data format error:", data);
                setIncidents([]);
            }
        } catch (error) {
            console.error("Failed to fetch queue:", error);
            setIncidents([]);
        }
    };

    const handleApprove = async (incidentId) => {
        try {
            const res = await fetch(`/api/dispatcher/${incidentId}/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    decision: 'approved',
                    priority: selectedIncident.priority // Send selected priority
                })
            });
            if (res.ok) {
                // Optimistic update
                setIncidents(prev => prev.map(inc =>
                    inc.incident_id === incidentId ? { ...inc, status: 'dispatched', priority: selectedIncident.priority } : inc
                ));
                setSelectedIncident(null);
            }
        } catch (error) {
            console.error("Approve failed:", error);
        }
    };

    const handleReject = async (incidentId) => {
        const reason = prompt("Enter rejection reason:");
        if (!reason) return;

        try {
            const res = await fetch(`/api/dispatcher/${incidentId}/reject`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason })
            });
            if (res.ok) {
                setIncidents(prev => prev.filter(inc => inc.incident_id !== incidentId));
                setSelectedIncident(null);
            }
        } catch (error) {
            console.error("Reject failed:", error);
        }
    };

    const filteredIncidents = incidents.filter(inc => {
        if (filter === 'pending_dispatch') return inc.status === 'pending_dispatch';
        if (filter === 'active') return ['dispatched', 'in_progress', 'reinforcement', 'escalated'].includes(inc.status);
        if (filter === 'resolved') return inc.status === 'resolved';
        return true;
    });

    return (
        <div className="min-h-screen bg-background text-foreground flex font-sans">

            {/* Sidebar */}
            <aside className="w-64 bg-card border-r border-border flex flex-col">
                <div className="p-6 border-b border-border">
                    <div className="flex items-center gap-3 mb-1">
                        <div className="w-8 h-8 bg-white text-black rounded-lg flex items-center justify-center">
                            <Radio size={18} />
                        </div>
                        <h1 className="font-bold text-lg tracking-tight">Dispatcher</h1>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <div className={`w-2 h-2 rounded-full ${wsStatus === 'connected' ? 'bg-green-500' : 'bg-red-500'}`}></div>
                        System {wsStatus === 'connected' ? 'Online' : 'Offline'}
                    </div>
                </div>

                <nav className="flex-1 p-4 space-y-1">
                    <button
                        onClick={() => setFilter('pending_dispatch')}
                        className={`w-full flex items-center justify-between px-4 py-3 rounded-lg text-sm font-medium transition-colors ${filter === 'pending_dispatch' ? 'bg-white text-black' : 'text-muted-foreground hover:bg-white/5 hover:text-white'}`}
                    >
                        <div className="flex items-center gap-3">
                            <AlertTriangle size={16} />
                            Pending
                        </div>
                        <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                            {incidents.filter(i => i.status === 'pending_dispatch').length}
                        </span>
                    </button>

                    <button
                        onClick={() => setFilter('active')}
                        className={`w-full flex items-center justify-between px-4 py-3 rounded-lg text-sm font-medium transition-colors ${filter === 'active' ? 'bg-white text-black' : 'text-muted-foreground hover:bg-white/5 hover:text-white'}`}
                    >
                        <div className="flex items-center gap-3">
                            <Activity size={16} />
                            Active Ops
                        </div>
                        <span className="bg-secondary text-muted-foreground text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                            {incidents.filter(i => ['dispatched', 'in_progress', 'reinforcement', 'escalated'].includes(i.status)).length}
                        </span>
                    </button>

                    <button
                        onClick={() => setFilter('resolved')}
                        className={`w-full flex items-center justify-between px-4 py-3 rounded-lg text-sm font-medium transition-colors ${filter === 'resolved' ? 'bg-white text-black' : 'text-muted-foreground hover:bg-white/5 hover:text-white'}`}
                    >
                        <div className="flex items-center gap-3">
                            <CheckCircle size={16} />
                            Resolved
                        </div>
                    </button>
                </nav>

                <div className="p-4 border-t border-border">
                    <div className="bg-secondary rounded-lg p-3">
                        <div className="text-xs text-muted-foreground mb-1">Active Units</div>
                        <div className="text-2xl font-bold">12/15</div>
                        <div className="w-full bg-black h-1 rounded-full mt-2 overflow-hidden">
                            <div className="bg-green-500 h-full w-[80%]"></div>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 flex overflow-hidden">

                {/* Incident List */}
                <div className="w-96 border-r border-border flex flex-col bg-background">
                    <div className="p-4 border-b border-border flex gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-2.5 text-muted-foreground" size={16} />
                            <input
                                className="w-full bg-secondary border-none rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white"
                                placeholder="Search incidents..."
                            />
                        </div>
                        <button className="p-2 bg-secondary rounded-lg text-muted-foreground hover:text-white">
                            <Filter size={18} />
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-3">
                        {filteredIncidents.length === 0 ? (
                            <div className="text-center text-muted-foreground py-10 text-sm">
                                No incidents found
                            </div>
                        ) : (
                            filteredIncidents.map(incident => (
                                <div
                                    key={incident.incident_id}
                                    onClick={() => setSelectedIncident(incident)}
                                    className={`p-4 rounded-xl border cursor-pointer transition-all hover:border-white/30 ${selectedIncident?.incident_id === incident.incident_id ? 'bg-card border-white shadow-lg' : 'bg-card border-border hover:bg-secondary'}`}
                                >
                                    <div className="flex justify-between items-start mb-2">
                                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${incident.priority === 'P1' ? 'bg-red-500/10 text-red-500 border-red-500/20' :
                                            incident.priority === 'P2' ? 'bg-orange-500/10 text-orange-500 border-orange-500/20' :
                                                'bg-blue-500/10 text-blue-500 border-blue-500/20'
                                            }`}>
                                            {incident.priority}
                                        </span>
                                        <span className="text-xs text-muted-foreground">{new Date(incident.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                    </div>
                                    <h3 className="font-semibold text-sm mb-1 line-clamp-1">{incident.incident_type}</h3>
                                    <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{incident.description}</p>
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <MapPin size={12} />
                                        <span className="truncate">Lat: {incident.location?.lat?.toFixed(4)}, Lon: {incident.location?.lon?.toFixed(4)}</span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Incident Detail View */}
                <div className="flex-1 bg-secondary/30 p-8 overflow-y-auto">
                    {selectedIncident ? (
                        <div className="max-w-4xl mx-auto space-y-6">

                            {/* Header Card */}
                            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
                                <div className="flex justify-between items-start mb-6">
                                    <div>
                                        <div className="flex items-center gap-3 mb-2">
                                            <h2 className="text-2xl font-bold">{selectedIncident.incident_type}</h2>
                                            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${selectedIncident.priority === 'P1' ? 'bg-red-500/10 text-red-500 border-red-500/20' :
                                                'bg-blue-500/10 text-blue-500 border-blue-500/20'
                                                }`}>
                                                {selectedIncident.priority} Priority
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                            <span className="flex items-center gap-1"><Clock size={14} /> {new Date(selectedIncident.created_at).toLocaleString()}</span>
                                            <span className="flex items-center gap-1"><MapPin size={14} /> {selectedIncident.location?.lat}, {selectedIncident.location?.lon}</span>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <div className="text-sm text-muted-foreground mb-1">Incident ID</div>
                                        <div className="font-mono font-bold">{selectedIncident.incident_id.slice(0, 8)}</div>
                                    </div>
                                </div>

                                <div className="bg-secondary/50 rounded-lg p-4 border border-border">
                                    <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Description</h4>
                                    <p className="text-sm leading-relaxed">{selectedIncident.description}</p>
                                </div>
                            </div>

                            {/* AI Analysis & Assets */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="bg-card border border-border rounded-xl p-6">
                                    <h3 className="font-semibold mb-4 flex items-center gap-2">
                                        <Shield size={18} /> AI Analysis
                                    </h3>
                                    <div className="space-y-4">
                                        <div>
                                            <div className="text-xs text-muted-foreground mb-1">Reasoning</div>
                                            <p className="text-sm">{selectedIncident.reasoning || "No analysis available."}</p>
                                        </div>
                                        <div>
                                            <div className="text-xs text-muted-foreground mb-1">Risks</div>
                                            <div className="flex flex-wrap gap-2">
                                                {selectedIncident.ai_analysis?.risks?.map((risk, i) => (
                                                    <span key={i} className="px-2 py-1 bg-red-500/10 text-red-500 border border-red-500/20 rounded text-xs">
                                                        {risk}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-card border border-border rounded-xl p-6">
                                    <h3 className="font-semibold mb-4 flex items-center gap-2">
                                        <Radio size={18} /> Recommended Assets
                                    </h3>
                                    <div className="space-y-3">
                                        {Array.isArray(selectedIncident.recommended_assets) && selectedIncident.recommended_assets.map((asset, i) => (
                                            <div key={i} className="flex items-center justify-between p-3 bg-secondary rounded-lg border border-border">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded bg-white/10 flex items-center justify-center">
                                                        {asset.type === 'ambulance' ? <Activity size={16} /> : <Shield size={16} />}
                                                    </div>
                                                    <div>
                                                        <div className="text-sm font-medium capitalize">{asset.type}</div>
                                                        <div className="text-xs text-muted-foreground">ID: {asset.id}</div>
                                                    </div>
                                                </div>
                                                <div className="text-xs font-mono text-green-500">Available</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Actions */}
                            {selectedIncident.status === 'pending_dispatch' && (
                                <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-4 shadow-lg shadow-black/50 sticky bottom-6">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <h3 className="font-bold">Dispatch Action Required</h3>
                                            <p className="text-sm text-muted-foreground">Review analysis and authorize deployment.</p>
                                        </div>

                                        {/* Edit Priority */}
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-medium text-muted-foreground">Priority:</span>
                                            <select
                                                className="bg-secondary border border-border rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-white"
                                                value={selectedIncident.priority}
                                                onChange={(e) => setSelectedIncident({ ...selectedIncident, priority: e.target.value })}
                                            >
                                                <option value="P1">P1 (Critical)</option>
                                                <option value="P2">P2 (High)</option>
                                                <option value="P3">P3 (Medium)</option>
                                                <option value="P4">P4 (Low)</option>
                                            </select>
                                        </div>
                                    </div>

                                    <div className="flex gap-3 justify-end">
                                        <button
                                            onClick={() => handleReject(selectedIncident.incident_id)}
                                            className="px-6 py-2 rounded-lg font-bold text-red-500 hover:bg-red-500/10 transition-colors"
                                        >
                                            Reject
                                        </button>
                                        <button
                                            onClick={() => handleApprove(selectedIncident.incident_id)}
                                            className="px-6 py-2 rounded-lg font-bold bg-white text-black hover:bg-gray-200 transition-colors flex items-center gap-2"
                                        >
                                            <CheckCircle size={18} />
                                            Approve & Dispatch
                                        </button>
                                    </div>
                                </div>
                            )}

                        </div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-muted-foreground opacity-50">
                            <Radio size={48} className="mb-4" />
                            <p>Select an incident to view details</p>
                        </div>
                    )}
                </div>
            </main>
        </div>
    )
}

export default DispatcherDashboard