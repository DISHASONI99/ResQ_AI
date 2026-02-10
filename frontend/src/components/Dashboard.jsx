import { useState } from 'react'
import { Activity, AlertTriangle, CheckCircle, Clock, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom';

function Dashboard() {
    const navigate = useNavigate();
    const [stats] = useState({
        activeIncidents: 12,
        pendingApproval: 3,
        resolvedToday: 28,
        avgResponseTime: '8.4 min',
    })

    const [recentIncidents] = useState([
        { id: 'INC-A8F3', type: 'Medical', priority: 'P1', location: 'MG Road, Bangalore', status: 'Active', time: '2 min ago' },
        { id: 'INC-B2D1', type: 'Fire', priority: 'P2', location: 'Indiranagar', status: 'Pending', time: '5 min ago' },
        { id: 'INC-C9E7', type: 'Accident', priority: 'P3', location: 'Koramangala', status: 'Resolved', time: '12 min ago' },
    ])

    return (
        <div className="animate-in fade-in duration-500">
            <h2 className="text-2xl font-bold mb-6">
                Dispatch Dashboard
            </h2>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <div className="bg-card border border-border rounded-xl p-6">
                    <div className="text-sm font-medium text-muted-foreground mb-2">Active Incidents</div>
                    <div className="text-3xl font-bold text-red-500 mb-1">{stats.activeIncidents}</div>
                    <div className="text-xs text-red-400 flex items-center gap-1">↑ 3 from yesterday</div>
                </div>
                <div className="bg-card border border-border rounded-xl p-6">
                    <div className="text-sm font-medium text-muted-foreground mb-2">Pending Approval</div>
                    <div className="text-3xl font-bold text-orange-500 mb-1">{stats.pendingApproval}</div>
                    <div className="text-xs text-muted-foreground">Requires HITL</div>
                </div>
                <div className="bg-card border border-border rounded-xl p-6">
                    <div className="text-sm font-medium text-muted-foreground mb-2">Resolved Today</div>
                    <div className="text-3xl font-bold text-green-500 mb-1">{stats.resolvedToday}</div>
                    <div className="text-xs text-green-400 flex items-center gap-1">↑ 12% from avg</div>
                </div>
                <div className="bg-card border border-border rounded-xl p-6">
                    <div className="text-sm font-medium text-muted-foreground mb-2">Avg Response Time</div>
                    <div className="text-3xl font-bold text-white mb-1">{stats.avgResponseTime}</div>
                    <div className="text-xs text-green-400 flex items-center gap-1">↓ 1.2 min improved</div>
                </div>
            </div>

            {/* Recent Incidents Table */}
            <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="p-6 border-b border-border flex justify-between items-center">
                    <h3 className="font-semibold text-lg">Recent Incidents</h3>
                    <button
                        className="text-sm text-muted-foreground hover:text-white flex items-center gap-1 transition-colors"
                        onClick={() => navigate('/incidents')}
                    >
                        View All <ArrowRight size={14} />
                    </button>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-secondary text-muted-foreground uppercase text-xs font-semibold">
                            <tr>
                                <th className="px-6 py-4">ID</th>
                                <th className="px-6 py-4">Type</th>
                                <th className="px-6 py-4">Priority</th>
                                <th className="px-6 py-4">Location</th>
                                <th className="px-6 py-4">Status</th>
                                <th className="px-6 py-4">Time</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {recentIncidents.map((incident) => (
                                <tr key={incident.id} className="hover:bg-secondary/50 transition-colors">
                                    <td className="px-6 py-4 font-medium font-mono">{incident.id}</td>
                                    <td className="px-6 py-4">{incident.type}</td>
                                    <td className="px-6 py-4">
                                        <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider border ${incident.priority === 'P1' ? 'bg-red-500/10 text-red-500 border-red-500/20' :
                                                incident.priority === 'P2' ? 'bg-orange-500/10 text-orange-500 border-orange-500/20' :
                                                    'bg-blue-500/10 text-blue-500 border-blue-500/20'
                                            }`}>
                                            {incident.priority}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-muted-foreground">{incident.location}</td>
                                    <td className="px-6 py-4">
                                        <span className={`flex items-center gap-2 ${incident.status === 'Active' ? 'text-red-500' :
                                                incident.status === 'Pending' ? 'text-orange-500' :
                                                    'text-green-500'
                                            }`}>
                                            {incident.status === 'Active' && <Activity size={14} />}
                                            {incident.status === 'Pending' && <Clock size={14} />}
                                            {incident.status === 'Resolved' && <CheckCircle size={14} />}
                                            {incident.status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-muted-foreground">{incident.time}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}

export default Dashboard