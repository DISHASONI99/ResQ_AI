import { useState, useEffect } from 'react'
import {
    Shield, MapPin, Phone, Clock, CheckCircle, AlertTriangle,
    Menu, ChevronDown, Activity, User, MessageSquare
} from 'lucide-react'

const CommanderDashboard = () => {
    const [incidents, setIncidents] = useState([])
    const [wsStatus, setWsStatus] = useState('disconnected')
    const [commanderId] = useState('CMD-001') // Hardcoded for demo

    // Fetch active incidents
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
            console.log("Commander WS Update:", update);

            if (update.type === 'commander_assigned' && update.commander.id === commanderId) {
                // New assignment for this commander
                setIncidents(prev => [update.incident, ...prev]);
            } else if (update.type === 'status_change') {
                // Update status locally
                setIncidents(prev => prev.map(inc =>
                    inc.incident_id === update.incident_id ? { ...inc, status: update.status } : inc
                ));
            }
        };

        return () => ws.close();
    }, [commanderId]);

    const fetchIncidents = async () => {
        try {
            const res = await fetch(`/api/commander/active?commander_id=${commanderId}`);
            if (!res.ok) throw new Error(`API Error: ${res.status}`);
            const data = await res.json();
            if (data.incidents && Array.isArray(data.incidents)) {
                setIncidents(data.incidents);
            } else if (Array.isArray(data)) {
                setIncidents(data);
            } else {
                console.error("Commander incidents data format error:", data);
                setIncidents([]);
            }
        } catch (error) {
            console.error("Failed to fetch incidents:", error);
            setIncidents([]);
        }
    };

    const updateStatus = async (incidentId, newStatus) => {
        try {
            const res = await fetch(`/api/commander/incidents/${incidentId}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            });
            if (res.ok) {
                setIncidents(prev => prev.map(inc =>
                    inc.incident_id === incidentId ? { ...inc, status: newStatus } : inc
                ));
            }
        } catch (error) {
            console.error("Status update failed:", error);
        }
    };

    return (
        <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">

            {/* Header */}
            <header className="bg-card border-b border-border px-8 py-4 flex justify-between items-center sticky top-0 z-10">
                <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-white text-black rounded-xl flex items-center justify-center shadow-lg shadow-white/10">
                        <Shield size={20} />
                    </div>
                    <div>
                        <h1 className="font-bold text-lg leading-none mb-1">Commander Dashboard</h1>
                        <div className="text-xs text-muted-foreground flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                            Active Duty • {commanderId}
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <button className="p-2 rounded-lg hover:bg-secondary transition-colors relative">
                        <MessageSquare size={20} />
                        <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border border-card"></span>
                    </button>
                    <div className="w-8 h-8 rounded-full bg-secondary border border-border flex items-center justify-center">
                        <User size={16} />
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 p-8 max-w-7xl mx-auto w-full">

                <div className="flex justify-between items-center mb-8">
                    <h2 className="text-2xl font-bold">Active Operations</h2>
                    <div className="flex gap-2">
                        <span className="px-3 py-1 bg-secondary rounded-full text-xs font-medium border border-border">Total: {incidents.length}</span>
                        <span className="px-3 py-1 bg-red-500/10 text-red-500 rounded-full text-xs font-medium border border-red-500/20">Critical: {incidents.filter(i => i.priority === 'P1').length}</span>
                    </div>
                </div>

                <div className="grid grid-cols-1 gap-6">
                    {incidents.length === 0 ? (
                        <div className="text-center py-20 text-muted-foreground bg-card border border-border rounded-xl border-dashed">
                            <Shield size={48} className="mx-auto mb-4 opacity-20" />
                            <p>No active incidents assigned.</p>
                            <p className="text-sm">Stand by for dispatch.</p>
                        </div>
                    ) : (
                        incidents.map(incident => (
                            <div key={incident.incident_id} className="bg-card border border-border rounded-xl overflow-hidden shadow-sm transition-all hover:shadow-md hover:border-white/20">

                                {/* Incident Header */}
                                <div className="p-6 border-b border-border flex flex-col md:flex-row justify-between gap-4">
                                    <div className="flex items-start gap-4">
                                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${incident.priority === 'P1' ? 'bg-red-500 text-white shadow-lg shadow-red-500/20' :
                                            incident.priority === 'P2' ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20' :
                                                'bg-blue-500 text-white shadow-lg shadow-blue-500/20'
                                            }`}>
                                            <AlertTriangle size={24} />
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-3 mb-1">
                                                <h3 className="text-xl font-bold">{incident.incident_type}</h3>
                                                <span className="text-xs font-mono text-muted-foreground">#{incident.incident_id.slice(0, 8)}</span>
                                            </div>
                                            <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                                <span className="flex items-center gap-1"><Clock size={14} /> {new Date(incident.created_at).toLocaleTimeString()}</span>
                                                <span className="flex items-center gap-1"><MapPin size={14} /> {incident.location?.lat?.toFixed(4)}, {incident.location?.lon?.toFixed(4)}</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-3">
                                        <div className="text-right mr-2">
                                            <div className="text-xs text-muted-foreground mb-1">Current Status</div>
                                            <div className="font-bold capitalize">{incident.status.replace('_', ' ')}</div>
                                        </div>

                                        {/* Status Dropdown */}
                                        <div className="relative group">
                                            <button className="flex items-center gap-2 bg-white text-black px-4 py-2 rounded-lg font-bold hover:bg-gray-200 transition-colors">
                                                Update Status
                                                <ChevronDown size={16} />
                                            </button>
                                            <div className="absolute right-0 mt-2 w-48 bg-card border border-border rounded-xl shadow-xl overflow-hidden hidden group-hover:block z-20">
                                                {[
                                                    { val: 'in_progress', label: 'In Progress', color: 'text-blue-500' },
                                                    { val: 'reinforcement', label: 'Request Backup', color: 'text-orange-500' },
                                                    { val: 'escalated', label: 'Escalate (P1)', color: 'text-red-500' },
                                                    { val: 'resolved', label: 'Mark Resolved', color: 'text-green-500' }
                                                ].map(opt => (
                                                    <button
                                                        key={opt.val}
                                                        onClick={() => updateStatus(incident.incident_id, opt.val)}
                                                        className={`w-full text-left px-4 py-3 text-sm font-medium hover:bg-secondary transition-colors ${opt.color}`}
                                                    >
                                                        {opt.label}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Incident Body */}
                                <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-8">

                                    {/* Description */}
                                    <div className="md:col-span-2 space-y-6">
                                        <div>
                                            <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">Situation Report</h4>
                                            <p className="text-sm leading-relaxed bg-secondary/30 p-4 rounded-lg border border-border">
                                                {incident.description}
                                            </p>
                                        </div>

                                        <div>
                                            <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">Dispatched Assets</h4>
                                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                                {Array.isArray(incident.recommended_assets) && incident.recommended_assets.map((asset, i) => (
                                                    <div key={i} className="flex items-center gap-3 p-3 bg-secondary rounded-lg border border-border">
                                                        <div className="w-8 h-8 rounded bg-white/10 flex items-center justify-center">
                                                            <Activity size={16} />
                                                        </div>
                                                        <div>
                                                            <div className="text-sm font-medium capitalize">{asset.type}</div>
                                                            <div className="text-xs text-green-500 flex items-center gap-1">
                                                                <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                                                                En Route (5m)
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Contact Info */}
                                    <div className="bg-secondary/20 rounded-xl p-6 border border-border h-fit">
                                        <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-4">Public Contact</h4>
                                        <div className="space-y-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                                                    <User size={14} />
                                                </div>
                                                <div>
                                                    <div className="text-xs text-muted-foreground">Reporter</div>
                                                    <div className="text-sm font-medium">Anonymous</div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                                                    <Phone size={14} />
                                                </div>
                                                <div>
                                                    <div className="text-xs text-muted-foreground">Phone</div>
                                                    <div className="text-sm font-medium">+91 98765 43210</div>
                                                </div>
                                            </div>
                                            <button className="w-full mt-2 bg-white text-black font-bold py-2 rounded-lg text-sm hover:bg-gray-200 transition-colors">
                                                Call Reporter
                                            </button>
                                        </div>
                                    </div>

                                </div>
                            </div>
                        ))
                    )}
                </div>
            </main>
        </div>
    )
}

export default CommanderDashboard