import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import IncidentForm from './components/IncidentForm'
import WhatsAppSimulator from './components/WhatsAppSimulator'
import IncidentsPage from './components/IncidentsPage'

import LandingPage from './pages/LandingPage'
import DispatcherDashboard from './pages/DispatcherDashboard'
import CommanderDashboard from './pages/CommanderDashboard'

function App() {
    return (
        <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/dispatcher" element={<DispatcherDashboard />} />
            <Route path="/commander" element={<CommanderDashboard />} />

            <Route element={<Layout />}>
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="incident" element={<IncidentForm />} />
                <Route path="whatsapp" element={<WhatsAppSimulator />} />
                <Route path="incidents" element={<IncidentsPage />} />
            </Route>
        </Routes>
    )
}

export default App