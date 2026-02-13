import { useState, useEffect, useRef } from 'react'
import { Send, Loader } from 'lucide-react'

function ChatInterface() {
    const [sessionId, setSessionId] = useState(null)
    const [messages, setMessages] = useState([])
    const [inputText, setInputText] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [role, setRole] = useState('dispatcher')
    const messagesEndRef = useRef(null)

    // Generate session ID on mount
    useEffect(() => {
        const newSessionId = crypto.randomUUID()
        setSessionId(newSessionId)
    }, [])

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const sendMessage = async (e) => {
        e.preventDefault()
        if (!inputText.trim() || isLoading) return

        const userMessage = {
            role: 'user',
            content: inputText,
            timestamp: new Date().toISOString(),
        }

        // Add user message immediately
        setMessages(prev => [...prev, userMessage])
        setInputText('')
        setIsLoading(true)

        try {
            const res = await fetch('/api/chat/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: inputText,
                    role: role,
                }),
            })

            if (!res.ok) throw new Error('Failed to send message')

            const data = await res.json()

            // Add AI response
            const aiMessage = {
                role: 'assistant',
                content: data.ai_response,
                timestamp: data.timestamp,
                metadata: data.incident_data,
            }

            setMessages(prev => [...prev, aiMessage])
        } catch (error) {
            console.error('Error sending message:', error)
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: '❌ Failed to process message. Please try again.',
                timestamp: new Date().toISOString(),
            }])
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="fade-in" style={{ height: 'calc(100vh - 200px)', display: 'flex', flexDirection: 'column' }}>
            <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem', fontWeight: 600 }}>
                ResQ AI Chat
            </h2>

            {/* Role Selector */}
            <div className="role-selector" style={{ marginBottom: '1rem' }}>
                {['dispatcher', 'commander', 'public'].map((r) => (
                    <button
                        key={r}
                        className={`role-btn ${role === r ? 'active' : ''}`}
                        onClick={() => setRole(r)}
                    >
                        {r.charAt(0).toUpperCase() + r.slice(1)}
                    </button>
                ))}
            </div>

            {/* Chat Messages */}
            <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {messages.length === 0 && (
                        <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>
                            <p>👋 Welcome! Describe your emergency and I'll help you.</p>
                        </div>
                    )}

                    {messages.map((msg, idx) => (
                        <div
                            key={idx}
                            style={{
                                display: 'flex',
                                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                            }}
                        >
                            <div
                                style={{
                                    maxWidth: '70%',
                                    padding: '0.75rem 1rem',
                                    borderRadius: '12px',
                                    background: msg.role === 'user'
                                        ? 'var(--primary)'
                                        : 'var(--card-bg)',
                                    color: msg.role === 'user'
                                        ? 'white'
                                        : 'var(--text-primary)',
                                    border: msg.role === 'assistant'
                                        ? '1px solid var(--border)'
                                        : 'none',
                                }}
                            >
                                <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                                <div style={{
                                    fontSize: '0.75rem',
                                    marginTop: '0.25rem',
                                    opacity: 0.7,
                                }}>
                                    {new Date(msg.timestamp).toLocaleTimeString()}
                                </div>
                            </div>
                        </div>
                    ))}

                    {isLoading && (
                        <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                            <div style={{
                                padding: '0.75rem 1rem',
                                borderRadius: '12px',
                                background: 'var(--card-bg)',
                                border: '1px solid var(--border)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                            }}>
                                <Loader size={16} className="spin" />
                                <span>Analyzing...</span>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Input Form */}
                <form onSubmit={sendMessage} style={{
                    padding: '1rem',
                    borderTop: '1px solid var(--border)',
                    display: 'flex',
                    gap: '0.5rem',
                }}>
                    <input
                        className="input"
                        placeholder="Describe the emergency..."
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        disabled={isLoading}
                        style={{ flex: 1 }}
                    />
                    <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={isLoading || !inputText.trim()}
                    >
                        <Send size={18} />
                    </button>
                </form>
            </div>
        </div>
    )
}

export default ChatInterface
