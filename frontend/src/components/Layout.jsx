import { Outlet, NavLink } from 'react-router-dom'
import { LayoutDashboard, AlertTriangle, MessageSquare, Settings, Shield } from 'lucide-react'

function Layout() {
    return (
        <div className="flex min-h-screen bg-background text-foreground font-sans">
            <aside className="w-64 bg-card border-r border-border p-6 flex flex-col fixed h-full z-10">
                <div className="flex items-center gap-3 mb-10 px-2">
                    <div className="w-8 h-8 bg-white text-black rounded-lg flex items-center justify-center">
                        <Shield size={18} fill="black" />
                    </div>
                    <h1 className="font-bold text-xl tracking-tight">ResQ AI</h1>
                </div>

                <nav className="flex-1 space-y-1">
                    <NavLink
                        to="/"
                        className={({ isActive }) => `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${isActive ? 'bg-white text-black shadow-sm' : 'text-muted-foreground hover:bg-white/5 hover:text-white'}`}
                    >
                        <LayoutDashboard size={18} />
                        Home
                    </NavLink>
                    <NavLink
                        to="/incident"
                        className={({ isActive }) => `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${isActive ? 'bg-white text-black shadow-sm' : 'text-muted-foreground hover:bg-white/5 hover:text-white'}`}
                    >
                        <AlertTriangle size={18} />
                        New Incident
                    </NavLink>
                    <NavLink
                        to="/whatsapp"
                        className={({ isActive }) => `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${isActive ? 'bg-white text-black shadow-sm' : 'text-muted-foreground hover:bg-white/5 hover:text-white'}`}
                    >
                        <MessageSquare size={18} />
                        WhatsApp Sim
                    </NavLink>
                </nav>

                <div className="mt-auto pt-6 border-t border-border">
                    <div className="flex items-center gap-3 px-4 py-2 opacity-70 hover:opacity-100 transition-opacity">
                        <div className="w-6 h-6 bg-red-600 rounded flex items-center justify-center text-[10px] font-bold text-white">Q</div>
                        <span className="text-xs font-medium text-muted-foreground">Powered by Qdrant</span>
                    </div>
                </div>
            </aside>

            <main className="flex-1 ml-64 p-8 overflow-y-auto">
                <div className="max-w-5xl mx-auto animate-in fade-in duration-500">
                    <Outlet />
                </div>
            </main>
        </div>
    )
}

export default Layout
