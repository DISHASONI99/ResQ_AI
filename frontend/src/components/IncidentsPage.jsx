import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Search, Filter, ArrowUpDown,
  ChevronLeft, ChevronRight, MoreHorizontal,
  Activity, CheckCircle, Clock, AlertTriangle, Download, Plus
} from 'lucide-react';

// --- Mock Data Generator ---
const generateIncidents = (count) => {
  const types = ['Medical', 'Fire', 'Accident', 'Theft', 'Public Disturbance'];
  const locations = ['Downtown', 'North Station', 'West End', 'Harbor Area', 'Industrial District'];
  const statuses = ['Active', 'Pending', 'Resolved', 'Investigating'];

  return Array.from({ length: count }, (_, i) => ({
    id: `INC-${(1000 + i).toString(16).toUpperCase()}`,
    type: types[Math.floor(Math.random() * types.length)],
    priority: Math.random() > 0.8 ? 'P1' : Math.random() > 0.6 ? 'P2' : 'P3',
    location: locations[Math.floor(Math.random() * locations.length)],
    status: statuses[Math.floor(Math.random() * statuses.length)],
    time: `${Math.floor(Math.random() * 59) + 1} min ago`,
    timestamp: Date.now() - Math.floor(Math.random() * 10000000)
  }));
};

const MOCK_DATA = generateIncidents(64);

export default function IncidentsPage() {
  const navigate = useNavigate();

  // --- State ---
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [priorityFilter, setPriorityFilter] = useState('All');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;
  const [sortConfig, setSortConfig] = useState({ key: 'timestamp', direction: 'desc' });

  // --- Filtering & Sorting Logic ---
  const filteredData = useMemo(() => {
    let data = [...MOCK_DATA];

    // 1. Search
    if (searchTerm) {
      const lowerTerm = searchTerm.toLowerCase();
      data = data.filter(item =>
        item.id.toLowerCase().includes(lowerTerm) ||
        item.location.toLowerCase().includes(lowerTerm) ||
        item.type.toLowerCase().includes(lowerTerm)
      );
    }

    // 2. Filters
    if (statusFilter !== 'All') {
      data = data.filter(item => item.status === statusFilter);
    }
    if (priorityFilter !== 'All') {
      data = data.filter(item => item.priority === priorityFilter);
    }

    // 3. Sorting
    data.sort((a, b) => {
      if (a[sortConfig.key] < b[sortConfig.key]) return sortConfig.direction === 'asc' ? -1 : 1;
      if (a[sortConfig.key] > b[sortConfig.key]) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });

    return data;
  }, [searchTerm, statusFilter, priorityFilter, sortConfig]);

  // --- Pagination Logic ---
  const totalPages = Math.ceil(filteredData.length / itemsPerPage);
  const currentData = filteredData.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // --- Handlers ---
  const handleSort = (key) => {
    setSortConfig(current => ({
      key,
      direction: current.key === key && current.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  // --- NEW: Export to CSV Function ---
  const handleExportCSV = () => {
    const headers = ["ID", "Type", "Priority", "Location", "Status", "Time"];
    const rows = filteredData.map(item => [
      item.id, item.type, item.priority, item.location, item.status, item.time
    ]);
    const csvContent = [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", "incident_report.csv");
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 bg-secondary rounded-lg hover:bg-white/10 transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h2 className="text-2xl font-bold">Incident Logs</h2>
            <p className="text-sm text-muted-foreground">
              Viewing {filteredData.length} records • Last synced just now
            </p>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            className="flex items-center gap-2 px-4 py-2 bg-secondary border border-border rounded-lg hover:bg-white/10 transition-colors text-sm font-medium"
            onClick={handleExportCSV}
          >
            <Download size={16} /> Export CSV
          </button>

          <button
            className="flex items-center gap-2 px-4 py-2 bg-white text-black rounded-lg hover:bg-gray-200 transition-colors text-sm font-bold"
            onClick={() => navigate('/incident')}
          >
            <Plus size={16} /> New Incident
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="bg-card border border-border rounded-xl p-4 mb-6 flex flex-col md:flex-row gap-4">

        {/* Search */}
        <div className="flex-1 relative">
          <Search size={18} className="absolute left-3 top-2.5 text-muted-foreground" />
          <input
            type="text"
            className="w-full bg-secondary border-none rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white placeholder:text-muted-foreground"
            placeholder="Search by ID, Type, or Location..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {/* Filters */}
        <div className="flex gap-4">
          <select
            className="bg-secondary border-none rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white cursor-pointer"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="All">All Statuses</option>
            <option value="Active">Active</option>
            <option value="Pending">Pending</option>
            <option value="Resolved">Resolved</option>
          </select>

          <select
            className="bg-secondary border-none rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-white cursor-pointer"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
          >
            <option value="All">All Priorities</option>
            <option value="P1">P1 (Critical)</option>
            <option value="P2">P2 (High)</option>
            <option value="P3">P3 (Medium)</option>
          </select>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-secondary text-muted-foreground uppercase text-xs font-semibold">
              <tr>
                <th onClick={() => handleSort('id')} className="px-6 py-4 cursor-pointer hover:text-white transition-colors">
                  <div className="flex items-center gap-2">ID <ArrowUpDown size={14} /></div>
                </th>
                <th className="px-6 py-4">Type</th>
                <th onClick={() => handleSort('priority')} className="px-6 py-4 cursor-pointer hover:text-white transition-colors">Priority</th>
                <th className="px-6 py-4">Location</th>
                <th className="px-6 py-4">Status</th>
                <th onClick={() => handleSort('timestamp')} className="px-6 py-4 cursor-pointer hover:text-white transition-colors">Time Logged</th>
                <th className="px-6 py-4">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {currentData.map((incident) => (
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
                  <td className="px-6 py-4">
                    <button className="p-1 rounded hover:bg-white/10 transition-colors text-muted-foreground hover:text-white">
                      <MoreHorizontal size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination Footer */}
      <div className="flex justify-between items-center mt-6 px-2">
        <div className="text-sm text-muted-foreground">
          Showing page {currentPage} of {totalPages}
        </div>
        <div className="flex gap-2">
          <button
            className="px-3 py-1 bg-secondary rounded-lg text-sm hover:bg-white/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
            disabled={currentPage === 1}
            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
          >
            <ChevronLeft size={16} /> Previous
          </button>
          <button
            className="px-3 py-1 bg-secondary rounded-lg text-sm hover:bg-white/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
            disabled={currentPage === totalPages}
            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}