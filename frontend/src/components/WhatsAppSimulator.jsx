import { useState, useRef, useEffect } from 'react'
import { Send, Image, Mic, MapPin, AlertTriangle, X, StopCircle, Play, Pause, Loader2 } from 'lucide-react'

function WhatsAppSimulator() {
    // Generate session ID for conversation memory
    const [sessionId] = useState(() => crypto.randomUUID())
    const [messages, setMessages] = useState([
        {
            id: 1,
            type: 'system',
            text: 'Welcome to ResQ AI Emergency Services. Describe your emergency, share your location, or send an image.',
            time: '10:00',
        },
    ])
    const [input, setInput] = useState('')
    const [isProcessing, setIsProcessing] = useState(false)
    const messagesEndRef = useRef(null)

    // Media state
    const [imagePreview, setImagePreview] = useState(null)
    const imageInputRef = useRef(null)

    // Audio state
    const [audioFile, setAudioFile] = useState(null)
    const [audioUrl, setAudioUrl] = useState(null)
    const [isRecording, setIsRecording] = useState(false)
    const [recordingTime, setRecordingTime] = useState(0)
    const mediaRecorderRef = useRef(null)
    const audioChunksRef = useRef([])
    const timerIntervalRef = useRef(null)
    const audioPlayerRef = useRef(null)
    const [isPlaying, setIsPlaying] = useState(false)

    // Location state
    const [isGettingLocation, setIsGettingLocation] = useState(false)
    const [currentLocation, setCurrentLocation] = useState(null)

    const [currentIncidentId, setCurrentIncidentId] = useState(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    // WebSocket for real-time updates
    useEffect(() => {
        const ws = new WebSocket('ws://localhost:8000/ws/incidents');

        ws.onmessage = (event) => {
            const update = JSON.parse(event.data);
            console.log("WebSocket update:", update);

            // Only show updates for the current incident
            if (update.incident_id === currentIncidentId) {
                if (update.type === 'commander_assigned') {
                    // Commander assigned - show detailed message
                    const commanderMsg = {
                        id: Date.now(),
                        type: 'system',
                        text: `🚨 **UPDATE: Help is on the way!**\n\n👮 **Commander:** ${update.commander.name}\n📞 **Contact:** ${update.commander.phone}\n\nStay calm.`,
                        time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
                    };
                    setMessages(prev => [...prev, commanderMsg]);
                } else if (update.type === 'status_change') {
                    // Status update
                    let statusText = "";
                    if (update.status === 'resolved') statusText = "✅ **Incident Resolved**\n\nOur team has marked this incident as resolved. Stay safe.";
                    else if (update.status === 'rejected') statusText = `❌ **Report Rejected**\n\nReason: ${update.reason}`;
                    else statusText = `ℹ️ **Status Update:** ${update.status.replace('_', ' ').toUpperCase()}`;

                    // Append commander info if available
                    if (update.commander_info) {
                        statusText += `\n\n👮 **Commander:** ${update.commander_info.name}\n📞 **Contact:** ${update.commander_info.phone}`;
                    }

                    const statusMsg = {
                        id: Date.now(),
                        type: 'system',
                        text: statusText,
                        time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
                    };
                    setMessages(prev => [...prev, statusMsg]);
                }
            }
        };

        return () => ws.close();
    }, [currentIncidentId]);

    // Image handlers
    const handleImageChange = (e) => {
        const file = e.target.files[0]
        if (file) {
            const url = URL.createObjectURL(file)
            setImagePreview({ file, url })
        }
    }

    const removeImage = () => {
        if (imagePreview) URL.revokeObjectURL(imagePreview.url)
        setImagePreview(null)
    }

    // Audio handlers
    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            mediaRecorderRef.current = new MediaRecorder(stream)
            audioChunksRef.current = []

            mediaRecorderRef.current.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data)
                }
            }

            mediaRecorderRef.current.onstop = () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
                const file = new File([audioBlob], "voice_note.webm", { type: 'audio/webm' })
                const url = URL.createObjectURL(audioBlob)

                setAudioFile(file)
                setAudioUrl(url)

                stream.getTracks().forEach(track => track.stop())
            }

            mediaRecorderRef.current.start()
            setIsRecording(true)

            setRecordingTime(0)
            timerIntervalRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1)
            }, 1000)

        } catch (error) {
            console.error("Error accessing microphone:", error)
            alert("Could not access microphone. Please ensure permissions are granted.")
        }
    }

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop()
            setIsRecording(false)
            clearInterval(timerIntervalRef.current)
        }
    }

    const removeAudio = () => {
        if (audioUrl) URL.revokeObjectURL(audioUrl)
        setAudioFile(null)
        setAudioUrl(null)
        setRecordingTime(0)
        setIsPlaying(false)
    }

    const togglePlayback = () => {
        if (audioPlayerRef.current) {
            if (isPlaying) {
                audioPlayerRef.current.pause()
            } else {
                audioPlayerRef.current.play()
            }
            setIsPlaying(!isPlaying)
        }
    }

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60)
        const secs = seconds % 60
        return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    // Location handler
    const getLocation = () => {
        if (!navigator.geolocation) {
            alert("Geolocation is not supported by your browser")
            return
        }

        setIsGettingLocation(true)

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const loc = {
                    lat: position.coords.latitude,
                    lon: position.coords.longitude
                }
                setCurrentLocation(loc)
                setIsGettingLocation(false)

                // Add location message to chat
                const locationMessage = {
                    id: Date.now(),
                    type: 'user',
                    text: `📍 Location shared: ${loc.lat.toFixed(4)}°, ${loc.lon.toFixed(4)}°`,
                    time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
                }
                setMessages((prev) => [...prev, locationMessage])
            },
            (error) => {
                console.error("Error getting location:", error)
                alert("Unable to retrieve your location. Please check permissions.")
                setIsGettingLocation(false)
            }
        )
    }

    const sendMessage = async () => {
        if ((!input.trim() && !imagePreview && !audioFile) || isProcessing) return

        // Add user message to chat
        const messageText = input.trim() || (imagePreview ? '📷 [Image]' : '') + (audioFile ? '🎤 [Voice]' : '') || 'Sent media'
        const userMessage = {
            id: Date.now(),
            type: 'user',
            text: messageText,
            image: imagePreview?.url,
            time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        }

        setMessages((prev) => [...prev, userMessage])
        setInput('')
        setIsProcessing(true)

        try {
            // Build FormData for multimodal request
            const formData = new FormData()
            formData.append('message', input.trim() || 'Check attached media')
            formData.append('role', 'public')
            formData.append('session_id', sessionId)

            // Add image if present
            if (imagePreview?.file) {
                formData.append('image', imagePreview.file)
            }

            // Add audio if present
            if (audioFile) {
                formData.append('audio', audioFile)
            }

            // Add location if set
            if (currentLocation) {
                formData.append('lat', currentLocation.lat)
                formData.append('lon', currentLocation.lon)
            }

            // Use multimodal endpoint
            const res = await fetch('/api/chat/multimodal', {
                method: 'POST',
                body: formData,
            })

            if (!res.ok) {
                const errorData = await res.json().catch(() => ({}))
                throw new Error(errorData.detail || 'Failed to connect to ResQ AI')
            }

            const data = await res.json()

            // Check for guardrails error/refusal
            if (data.incident_data?.error === 'Refused' || data.ai_response?.includes('error')) {
                const refusalResponse = {
                    id: Date.now() + 1,
                    type: 'system',
                    text: `🛡️ **Safety Check**\n\nYour message was flagged as inappropriate or outside the scope of emergency services.\n\nPlease provide a valid emergency report.`,
                    time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
                }
                setMessages((prev) => [...prev, refusalResponse])
                return
            }

            const systemResponse = {
                id: Date.now() + 1,
                type: 'system',
                text: data.ai_response || 'Processing your request...',
                time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
                incidentData: data.incident_data,
            }
            if (data.incident_data?.incident_id) {
                setCurrentIncidentId(data.incident_data.incident_id);
            }
            setMessages((prev) => [...prev, systemResponse])

            // Clear media after send
            removeImage()
            removeAudio()
            setCurrentLocation(null)

        } catch (error) {
            const errorResponse = {
                id: Date.now() + 1,
                type: 'system',
                text: `⚠️ Error: ${error.message}. Please try again later.`,
                time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
            }
            setMessages((prev) => [...prev, errorResponse])
        } finally {
            setIsProcessing(false)
        }
    }

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            sendMessage()
        }
    }

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h2 className="text-2xl font-bold mb-2 text-center">
                WhatsApp Simulation
            </h2>
            <p className="text-center text-muted-foreground mb-6 text-sm">
                Report emergencies with text, images, voice notes, or location
            </p>

            <div className="flex flex-col h-[600px] max-w-md mx-auto bg-black border border-border rounded-3xl overflow-hidden shadow-2xl">
                {/* Header */}
                <div className="bg-card p-4 flex items-center gap-3 border-b border-border">
                    <div className="w-10 h-10 rounded-full bg-white text-black flex items-center justify-center">
                        <AlertTriangle size={20} />
                    </div>
                    <div>
                        <div className="font-bold text-sm">ResQ AI Emergency</div>
                        <div className="text-xs text-muted-foreground">
                            {isProcessing ? 'typing...' : 'online'}
                        </div>
                    </div>
                </div>

                {/* Messages */}
                <div className="flex-1 p-4 overflow-y-auto flex flex-col gap-4 bg-black bg-[radial-gradient(#27272a_1px,transparent_1px)] bg-[size:20px_20px]">
                    {messages.map((msg) => (
                        <div key={msg.id} className={`max-w-[85%] p-3 rounded-2xl text-sm leading-relaxed ${msg.type === 'user'
                            ? 'bg-white text-black self-end rounded-br-none'
                            : 'bg-card text-foreground self-start rounded-bl-none border border-border'
                            }`}>
                            {msg.image && (
                                <img
                                    src={msg.image}
                                    alt="Attached"
                                    className="max-w-[200px] rounded-lg mb-2"
                                />
                            )}
                            <div className="whitespace-pre-wrap">{msg.text}</div>
                            <div className={`text-[10px] text-right mt-1 ${msg.type === 'user' ? 'text-gray-500' : 'text-muted-foreground'}`}>
                                {msg.time}
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>

                {/* Media Preview */}
                {(imagePreview || audioFile) && (
                    <div className="px-4 py-2 border-t border-border bg-card flex gap-2 items-center">
                        {imagePreview && (
                            <div className="relative inline-block">
                                <img
                                    src={imagePreview.url}
                                    alt="Preview"
                                    className="h-[50px] rounded"
                                />
                                <button
                                    onClick={removeImage}
                                    className="absolute -top-1 -right-1 bg-black/60 text-white rounded-full w-4 h-4 flex items-center justify-center"
                                >
                                    <X size={10} />
                                </button>
                            </div>
                        )}
                        {audioFile && (
                            <div className="flex items-center gap-2 bg-secondary px-3 py-1 rounded-full text-xs">
                                <button
                                    onClick={togglePlayback}
                                    className="w-6 h-6 rounded-full bg-white text-black flex items-center justify-center"
                                >
                                    {isPlaying ? <Pause size={10} /> : <Play size={10} className="ml-0.5" />}
                                </button>
                                <span>Voice note</span>
                                <button onClick={removeAudio} className="text-red-500">
                                    <X size={12} />
                                </button>
                                <audio ref={audioPlayerRef} src={audioUrl} onEnded={() => setIsPlaying(false)} />
                            </div>
                        )}
                    </div>
                )}

                {/* Input Area */}
                <div className="p-3 bg-card border-t border-border flex gap-2 items-end">
                    <button
                        className={`p-2 rounded-full transition-colors ${currentLocation ? 'bg-white text-black' : 'bg-secondary text-muted-foreground hover:bg-white/10'}`}
                        onClick={getLocation}
                        title="Share Location"
                        disabled={isGettingLocation}
                    >
                        {isGettingLocation ? <Loader2 size={18} className="animate-spin" /> : <MapPin size={18} />}
                    </button>

                    <button
                        className={`p-2 rounded-full transition-colors ${imagePreview ? 'bg-white text-black' : 'bg-secondary text-muted-foreground hover:bg-white/10'}`}
                        onClick={() => imageInputRef.current?.click()}
                        title="Send Image"
                    >
                        <Image size={18} />
                    </button>
                    <input
                        type="file"
                        accept="image/*"
                        hidden
                        ref={imageInputRef}
                        onChange={handleImageChange}
                    />

                    <button
                        className={`p-2 rounded-full transition-colors ${isRecording ? 'bg-red-500/20 text-red-500 animate-pulse' : audioFile ? 'bg-white text-black' : 'bg-secondary text-muted-foreground hover:bg-white/10'}`}
                        onClick={isRecording ? stopRecording : (audioFile ? null : startRecording)}
                        title={isRecording ? 'Stop Recording' : 'Send Voice Note'}
                        disabled={audioFile && !isRecording}
                    >
                        {isRecording ? <StopCircle size={18} /> : <Mic size={18} />}
                    </button>

                    <div className="flex-1 bg-input border border-border rounded-2xl px-4 py-2 flex items-center">
                        <input
                            className="bg-transparent w-full focus:outline-none text-sm placeholder:text-muted-foreground"
                            placeholder="Type a message..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                        />
                    </div>

                    <button
                        className="p-2 bg-white text-black rounded-full hover:bg-gray-200 transition-colors disabled:opacity-50"
                        onClick={sendMessage}
                        disabled={isProcessing}
                    >
                        <Send size={18} />
                    </button>
                </div>
            </div>
        </div>
    )
}

export default WhatsAppSimulator
