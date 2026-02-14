import React from 'react';
import { Users, Radio, Shield, ChevronRight, MessageSquare, FileText, Zap, CheckCircle, MapPin } from 'lucide-react';

const LandingPage = () => {
    const navigateToPortal = (path) => {
        window.location.href = path; // Simple navigation
    };

    return (
        <div className="min-h-screen bg-background text-foreground flex flex-col font-sans selection:bg-white selection:text-black">
            {/* Hero Section */}
            <div className="flex-grow flex flex-col justify-center relative overflow-hidden">

                {/* Subtle Grid Background */}
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#27272a_1px,transparent_1px),linear-gradient(to_bottom,#27272a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-10 pointer-events-none"></div>

                <div className="relative max-w-7xl mx-auto px-6 w-full py-20">

                    {/* Header */}
                    <div className="text-center mb-20">
                        <div className="inline-flex items-center justify-center w-16 h-16 bg-white text-black rounded-2xl mb-8 shadow-[0_0_40px_-10px_rgba(255,255,255,0.3)]">
                            <Shield className="w-8 h-8" strokeWidth={2.5} />
                        </div>
                        <h1 className="text-6xl md:text-8xl font-bold mb-6 tracking-tight">
                            ResQ AI
                        </h1>
                        <p className="text-xl text-muted-foreground tracking-widest uppercase mb-8 font-medium">
                            National Emergency Response System
                        </p>
                        <div className="inline-flex items-center gap-2 px-4 py-1.5 border border-white/10 rounded-full text-sm text-muted-foreground bg-white/5 backdrop-blur-sm">
                            <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
                            System Operational
                        </div>
                    </div>

                    {/* Role Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">

                        {/* Public Portal */}
                        <div className="group relative bg-card border border-border hover:border-white/50 transition-all duration-500 rounded-2xl p-8 hover:-translate-y-1">
                            <div className="mb-6 w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center group-hover:bg-white group-hover:text-black transition-colors duration-500">
                                <Users className="w-6 h-6" />
                            </div>
                            <h3 className="text-2xl font-bold mb-3">Public Portal</h3>
                            <p className="text-muted-foreground mb-8 leading-relaxed text-sm">
                                Report emergencies, share location, and track response status in real-time.
                            </p>
                            <div className="space-y-3">
                                <button onClick={() => navigateToPortal('/incident')} className="w-full flex items-center justify-between px-4 py-3 bg-secondary hover:bg-white hover:text-black rounded-lg transition-all duration-300 group/btn">
                                    <span className="flex items-center gap-3 text-sm font-medium">
                                        <FileText className="w-4 h-4" />
                                        New Incident
                                    </span>
                                    <ChevronRight className="w-4 h-4 opacity-50 group-hover/btn:translate-x-1 transition-transform" />
                                </button>
                                <button onClick={() => navigateToPortal('/whatsapp')} className="w-full flex items-center justify-between px-4 py-3 bg-secondary hover:bg-white hover:text-black rounded-lg transition-all duration-300 group/btn">
                                    <span className="flex items-center gap-3 text-sm font-medium">
                                        <MessageSquare className="w-4 h-4" />
                                        WhatsApp Chat
                                    </span>
                                    <ChevronRight className="w-4 h-4 opacity-50 group-hover/btn:translate-x-1 transition-transform" />
                                </button>
                            </div>
                        </div>

                        {/* Dispatcher Console */}
                        <div onClick={() => navigateToPortal('/dispatcher')} className="group relative bg-card border border-border hover:border-white/50 transition-all duration-500 rounded-2xl p-8 hover:-translate-y-1 cursor-pointer flex flex-col">
                            <div className="mb-6 w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center group-hover:bg-white group-hover:text-black transition-colors duration-500">
                                <Radio className="w-6 h-6" />
                            </div>
                            <h3 className="text-2xl font-bold mb-3">Dispatcher</h3>
                            <p className="text-muted-foreground mb-8 leading-relaxed text-sm flex-grow">
                                Review incoming alerts, verify incidents, and dispatch emergency units.
                            </p>
                            <div className="flex items-center gap-2 text-sm font-medium text-white group-hover:gap-3 transition-all mt-auto">
                                Enter Console
                                <ChevronRight className="w-4 h-4" />
                            </div>
                        </div>

                        {/* Commander Dashboard */}
                        <div onClick={() => navigateToPortal('/commander')} className="group relative bg-card border border-border hover:border-white/50 transition-all duration-500 rounded-2xl p-8 hover:-translate-y-1 cursor-pointer flex flex-col">
                            <div className="mb-6 w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center group-hover:bg-white group-hover:text-black transition-colors duration-500">
                                <Shield className="w-6 h-6" />
                            </div>
                            <h3 className="text-2xl font-bold mb-3">Commander</h3>
                            <p className="text-muted-foreground mb-8 leading-relaxed text-sm flex-grow">
                                Manage field operations, update status, and coordinate response teams.
                            </p>
                            <div className="flex items-center gap-2 text-sm font-medium text-white group-hover:gap-3 transition-all mt-auto">
                                Enter Dashboard
                                <ChevronRight className="w-4 h-4" />
                            </div>
                        </div>

                    </div>
                </div>
            </div>

            {/* Footer */}
            <footer className="border-t border-white/5 py-8 bg-black">
                <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-3 opacity-60 hover:opacity-100 transition-opacity">
                        <div className="w-6 h-6 bg-red-600 rounded flex items-center justify-center text-[10px] font-bold text-white">Q</div>
                        <span className="text-sm text-muted-foreground">Powered by Qdrant</span>
                    </div>
                    <div className="text-muted-foreground text-sm">
                        © 2026 ResQ AI
                    </div>
                </div>
            </footer>
        </div>
    );
};

export default LandingPage;