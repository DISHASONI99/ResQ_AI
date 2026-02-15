import { useState, useCallback, useEffect, useRef } from 'react'
import {
    Send, MapPin, Mic, AlertTriangle, Shield, XCircle, Crosshair, X,
    Image as ImageIcon, FileAudio, Trash2, StopCircle, Play, Pause, Loader2
} from 'lucide-react'
import { GoogleMap, useJsApiLoader, Marker } from '@react-google-maps/api'

// --- Map Configuration ---
const mapContainerStyle = {
    width: '100%',
    height: '400px',
    borderRadius: '0.75rem'
};

const defaultCenter = {
    lat: 40.7128,
    lng: -74.0060
};

// --- Audio Waveform Visualizer ---
const AudioWaveform = ({ file }) => {
    const canvasRef = useRef(null);
    const [duration, setDuration] = useState(0);

    useEffect(() => {
        if (!file || !canvasRef.current) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();

        const fileReader = new FileReader();
        fileReader.onload = async (e) => {
            const arrayBuffer = e.target.result;
            try {
                const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
                setDuration(audioBuffer.duration);
                drawWaveform(audioBuffer, canvas, ctx);
            } catch (error) {
                console.error("Error decoding audio data", error);
            }
        };
        fileReader.readAsArrayBuffer(file);

        return () => {
            audioContext.close();
        };
    }, [file]);

    const drawWaveform = (audioBuffer, canvas, ctx) => {
        const width = canvas.width;
        const height = canvas.height;
        const data = audioBuffer.getChannelData(0);
        const step = Math.ceil(data.length / width);
        const amp = height / 2;

        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = '#ffffff'; // White waveform
        ctx.beginPath();

        for (let i = 0; i < width; i++) {
            let min = 1.0;
            let max = -1.0;
            for (let j = 0; j < step; j++) {
                const datum = data[(i * step) + j];
                if (datum < min) min = datum;
                if (datum > max) max = datum;
            }
            ctx.fillRect(i, (1 + min) * amp, 1, Math.max(1, (max - min) * amp));
        }
    };

    return (
        <div className="w-full flex flex-col gap-1">
            <canvas
                ref={canvasRef}
                width={300}
                height={50}
                className="w-full h-[50px] bg-white/5 rounded"
            />
            <div className="text-xs text-muted-foreground text-right">
                {duration > 0 ? `${duration.toFixed(1)}s` : 'Loading...'}
            </div>
        </div>
    );
};

// --- Main Component ---
function IncidentForm() {
    // Form State
    const [formData, setFormData] = useState({
        text: '',
        role: 'public',
        latitude: '',
        longitude: ''
    })

    // Media State
    const [imagePreview, setImagePreview] = useState(null);

    // Audio State
    const [audioFile, setAudioFile] = useState(null);
    const [audioUrl, setAudioUrl] = useState(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const audioPlayerRef = useRef(null);

    // Transcription State
    const [transcription, setTranscription] = useState('');
    const [isTranscribing, setIsTranscribing] = useState(false);

    // Recording State
    const [isRecording, setIsRecording] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const timerIntervalRef = useRef(null);

    const [isEditingPriority, setIsEditingPriority] = useState(false)

    // UI State
    const [isLoading, setIsLoading] = useState(false)
    const [response, setResponse] = useState(null)
    const [safetyError, setSafetyError] = useState(null)

    // Map & Location State
    const [isMapOpen, setIsMapOpen] = useState(false)
    const [locationStatus, setLocationStatus] = useState(null)

    // Load Google Maps
    const { isLoaded } = useJsApiLoader({
        id: 'google-map-script',
        googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY
    });


    // --- Media Handlers ---
    const handleImageChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            const url = URL.createObjectURL(file);
            setImagePreview({ file, url });
        }
    };

    const removeImage = () => {
        if (imagePreview) URL.revokeObjectURL(imagePreview.url);
        setImagePreview(null);
    };

    // --- Transcription Logic ---
    const handleTranscribe = async (file) => {
        if (!file) return;

        setIsTranscribing(true);
        setTranscription(''); // Clear previous

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('/api/transcribe', {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                let errorDetails = res.statusText;
                try {
                    const errorJson = await res.json();
                    if (errorJson.detail) errorDetails = errorJson.detail;
                }
                catch (e) { /* ignore JSON parsing error */ }

                throw new Error(`Server ${res.status}: ${errorDetails}`);
            }

            const data = await res.json();
            setTranscription(data.text);

        }
        catch (error) {
            console.error("Transcription error:", error);
            setTranscription(`⚠️ Error: ${error.message}`);
        }
        finally {
            setIsTranscribing(false);
        }
    };

    // --- Audio Logic (Record & Play) ---
    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorderRef.current = new MediaRecorder(stream);
            audioChunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorderRef.current.onstop = () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                const file = new File([audioBlob], "voice_note.webm", { type: 'audio/webm' });
                const url = URL.createObjectURL(audioBlob);

                setAudioFile(file);
                setAudioUrl(url);

                stream.getTracks().forEach(track => track.stop());

                // AUTO-TRANSCRIBE ON STOP
                handleTranscribe(file);
            };

            mediaRecorderRef.current.start();
            setIsRecording(true);

            setRecordingTime(0);
            timerIntervalRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);

        } catch (error) {
            console.error("Error accessing microphone:", error);
            alert("Could not access microphone. Please ensure permissions are granted.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            clearInterval(timerIntervalRef.current);
        }
    };

    const removeAudio = () => {
        if (audioUrl) {
            URL.revokeObjectURL(audioUrl);
        }
        setAudioFile(null);
        setAudioUrl(null);
        setRecordingTime(0);
        setIsPlaying(false);
        setTranscription('');
    };

    const handleAudioChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            const url = URL.createObjectURL(file);
            setAudioFile(file);
            setAudioUrl(url);
            handleTranscribe(file);
        }
    };

    const togglePlayback = () => {
        if (audioPlayerRef.current) {
            if (isPlaying) {
                audioPlayerRef.current.pause();
            } else {
                audioPlayerRef.current.play();
            }
            setIsPlaying(!isPlaying);
        }
    };

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    // --- Geolocation Logic ---
    const handleUseMyLocation = () => {
        if (!navigator.geolocation) {
            alert("Geolocation is not supported by your browser");
            return;
        }

        setLocationStatus('loading');

        navigator.geolocation.getCurrentPosition(
            (position) => {
                setFormData(prev => ({
                    ...prev,
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                }));
                setLocationStatus('success');
            },
            (error) => {
                console.error("Error getting location:", error);
                alert("Unable to retrieve your location. Please check permissions.");
                setLocationStatus('error');
            }
        );
    };

    // --- Map Handlers ---
    const onMapClick = useCallback((e) => {
        setFormData(prev => ({
            ...prev,
            latitude: e.latLng.lat(),
            longitude: e.latLng.lng()
        }));
    }, []);

    const onMarkerDragEnd = useCallback((e) => {
        setFormData(prev => ({
            ...prev,
            latitude: e.latLng.lat(),
            longitude: e.latLng.lng()
        }));
    }, []);

    // --- WebSocket for Real-time Updates ---
    useEffect(() => {
        if (!response?.incident_id) return;

        const ws = new WebSocket('ws://localhost:8000/ws/incidents');

        ws.onmessage = (event) => {
            const update = JSON.parse(event.data);

            // Only update for current incident
            if (update.incident_id === response.incident_id) {
                if (update.type === 'status_change') {
                    setResponse(prev => ({
                        ...prev,
                        status: update.status,
                        priority: update.priority || prev.priority,
                        commander_info: update.commander_info // Store commander info
                    }));
                }
            }
        };

        return () => ws.close();
    }, [response?.incident_id]);

    const handleSubmit = async (e) => {
        e.preventDefault()
        setIsLoading(true)
        setSafetyError(null)

        try {
            // Validation: Must have at least one input (text, audio, or image)
            if (!formData.text.trim() && !audioFile && !imagePreview) {
                alert("Please provide a description, audio, or image to report an incident.");
                setIsLoading(false);
                return;
            }

            const formDataPayload = new FormData();

            let fullText = formData.text;
            if (transcription && !transcription.startsWith('⚠️')) {
                fullText = `${formData.text}\n[Audio Transcription: ${transcription}]`;
            }
            formDataPayload.append('text', fullText);
            formDataPayload.append('role', formData.role);

            if (formData.latitude && formData.longitude) {
                formDataPayload.append('lat', formData.latitude);
                formDataPayload.append('lon', formData.longitude);
            }

            if (imagePreview?.file) {
                formDataPayload.append('image', imagePreview.file);
            }

            if (audioFile) {
                formDataPayload.append('audio', audioFile);
            }

            const res = await fetch('/api/incidents/multimodal', {
                method: 'POST',
                body: formDataPayload,
            })

            if (res.status === 446) {
                setSafetyError({ type: 'input', message: 'Your message was flagged for safety.' })
                return
            }
            if (res.status === 246) {
                setSafetyError({ type: 'output', message: 'Response failed safety check.' })
                return
            }
            if (!res.ok) {
                const errorData = await res.json()
                throw new Error(errorData.detail || 'Failed to process incident')
            }

            const data = await res.json()
            setResponse(data)
        } catch (error) {
            if (error.message.includes('flagged for safety')) {
                setSafetyError({ type: 'input', message: error.message })
            } else {
                setResponse({ error: 'Failed to process incident: ' + error.message })
            }
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h2 className="text-2xl font-bold mb-6">
                Report New Incident
            </h2>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                {/* --- Left Column: Input Form --- */}
                <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
                    <h3 className="text-lg font-semibold mb-6">Incident Details</h3>

                    <form onSubmit={handleSubmit}>
                        <div className="mb-6">
                            <label className="block text-sm font-medium text-muted-foreground mb-2">Description</label>
                            <textarea
                                className="w-full bg-input border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:ring-1 focus:ring-white min-h-[140px] resize-y"
                                placeholder="Describe the emergency situation..."
                                value={formData.text}
                                onChange={(e) => setFormData({ ...formData, text: e.target.value })}
                            />
                        </div>

                        {/* --- File Uploads & Recording --- */}
                        <div className="mb-6">
                            <div className="grid grid-cols-2 gap-4">
                                {/* Image Upload */}
                                <label className={`flex flex-col items-center justify-center gap-2 p-4 rounded-lg border cursor-pointer transition-all ${imagePreview ? 'bg-white text-black border-white' : 'bg-secondary border-border hover:bg-white/10'}`}>
                                    <div className="flex items-center gap-2">
                                        <ImageIcon size={18} />
                                        {imagePreview ? 'Change Image' : 'Upload Image'}
                                    </div>
                                    <input type="file" accept="image/*" hidden onChange={handleImageChange} />
                                </label>

                                {/* Audio Recorder */}
                                {!audioFile && (
                                    <button
                                        type="button"
                                        onClick={isRecording ? stopRecording : startRecording}
                                        className={`flex flex-col items-center justify-center gap-2 p-4 rounded-lg border transition-all ${isRecording ? 'bg-red-500/10 text-red-500 border-red-500/50 animate-pulse' : 'bg-secondary border-border hover:bg-white/10'}`}
                                    >
                                        <div className="flex items-center gap-2">
                                            {isRecording ? <StopCircle size={18} /> : <Mic size={18} />}
                                            {isRecording ? `Stop (${formatTime(recordingTime)})` : 'Record Audio'}
                                        </div>
                                    </button>
                                )}

                                {/* Placeholder when audio exists */}
                                {audioFile && (
                                    <div className="flex items-center justify-center gap-2 p-4 rounded-lg bg-secondary border border-border opacity-50 cursor-not-allowed">
                                        <Mic size={18} />
                                        Recorded
                                    </div>
                                )}
                            </div>

                            {/* Image Preview */}
                            {imagePreview && (
                                <div className="mt-4 relative inline-block w-full">
                                    <img
                                        src={imagePreview.url}
                                        alt="Preview"
                                        className="w-full max-h-[200px] object-cover rounded-lg border border-border"
                                    />
                                    <button
                                        type="button"
                                        onClick={removeImage}
                                        className="absolute top-2 right-2 bg-black/60 text-white p-1 rounded-full hover:bg-black/80 transition-colors"
                                    >
                                        <X size={14} />
                                    </button>
                                </div>
                            )}

                            {/* Audio Player, Waveform & Transcription */}
                            {audioFile && (
                                <div className="mt-4 p-4 border border-border rounded-lg bg-card/50">
                                    <div className="flex items-center gap-2 mb-3">
                                        <FileAudio size={16} className="text-white" />
                                        <span className="text-sm font-medium">Voice Note Attached</span>
                                        <button
                                            type="button"
                                            onClick={removeAudio}
                                            className="ml-auto text-red-500 hover:text-red-400 transition-colors"
                                            title="Delete Recording"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>

                                    {/* Waveform & Player */}
                                    <div className="flex items-center gap-4">
                                        <button
                                            type="button"
                                            onClick={togglePlayback}
                                            className="flex-shrink-0 w-10 h-10 rounded-full bg-white text-black flex items-center justify-center hover:bg-gray-200 transition-colors"
                                        >
                                            {isPlaying ? <Pause size={18} fill="black" /> : <Play size={18} fill="black" className="ml-0.5" />}
                                        </button>

                                        <AudioWaveform file={audioFile} />

                                        <audio
                                            ref={audioPlayerRef}
                                            src={audioUrl}
                                            onEnded={() => setIsPlaying(false)}
                                        />
                                    </div>

                                    {/* --- TRANSCRIPTION DISPLAY --- */}
                                    <div className="mt-4 p-3 bg-secondary rounded-md border border-border text-sm text-muted-foreground">
                                        {isTranscribing ? (
                                            <div className="flex items-center gap-2 text-white">
                                                <Loader2 size={14} className="animate-spin" />
                                                <span>Transcribing audio...</span>
                                            </div>
                                        ) : transcription ? (
                                            <div>
                                                <div className="font-semibold mb-1 text-xs text-muted-foreground uppercase tracking-wider">TRANSCRIPTION</div>
                                                <p className="leading-relaxed text-foreground">{transcription}</p>
                                            </div>
                                        ) : (
                                            <span className="italic">No transcription available</span>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* --- Location Section --- */}
                        <div className="mb-6">
                            <div className="flex justify-between items-center mb-2">
                                <label className="text-sm font-medium text-muted-foreground">Location (Optional)</label>
                                <button
                                    type="button"
                                    className="text-sm flex items-center gap-1 text-white hover:underline bg-transparent border-none cursor-pointer"
                                    onClick={handleUseMyLocation}
                                >
                                    <Crosshair size={14} />
                                    {locationStatus === 'loading' ? 'Locating...' : 'Use My Location'}
                                </button>
                            </div>

                            <div className="flex gap-2">
                                <input
                                    className="w-full bg-input border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:ring-1 focus:ring-white"
                                    placeholder="Latitude"
                                    type="number"
                                    step="any"
                                    value={formData.latitude}
                                    onChange={(e) => setFormData({ ...formData, latitude: e.target.value })}
                                />
                                <input
                                    className="w-full bg-input border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:ring-1 focus:ring-white"
                                    placeholder="Longitude"
                                    type="number"
                                    step="any"
                                    value={formData.longitude}
                                    onChange={(e) => setFormData({ ...formData, longitude: e.target.value })}
                                />
                                <button type="button" className="px-4 bg-secondary border border-border rounded-lg hover:bg-white/10 transition-colors" onClick={() => setIsMapOpen(true)}>
                                    <MapPin size={18} />
                                </button>
                            </div>
                        </div>

                        <button
                            type="submit"
                            className="w-full bg-white text-black font-bold py-3 rounded-lg hover:bg-gray-200 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                            disabled={isLoading}
                        >
                            {isLoading ? 'Processing...' : <><Send size={18} /> Submit Incident</>}
                        </button>
                    </form>
                </div>

                {/* --- Right Column: Response / HITL --- */}
                <div>
                    {safetyError && (
                        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 mb-4 flex items-center gap-4">
                            <XCircle size={24} className="text-red-500 flex-shrink-0" />
                            <div>
                                <div className="font-bold text-red-500 mb-1">🛡️ Safety Check Failed</div>
                                <div className="text-sm text-red-200">{safetyError.message}</div>
                            </div>
                        </div>
                    )}

                    {response ? (
                        <div className={`bg-card border border-border rounded-xl p-6 shadow-sm ${response.requires_approval ? 'ring-1 ring-white/20' : ''}`}>
                            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                {response.requires_approval && <AlertTriangle className="text-yellow-500" size={20} />}
                                {response.requires_approval ? 'Approval Required' : 'Response'}
                            </h3>
                            <div className="space-y-4">
                                <div>
                                    <span className="text-sm text-muted-foreground block mb-1">Incident ID</span>
                                    <div className="font-mono font-bold">{response.incident_id}</div>
                                </div>
                                <div>
                                    <span className="text-sm text-muted-foreground block mb-1">Priority</span>
                                    <div>
                                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider
                                            ${response.priority === 'P1' ? 'bg-red-500/20 text-red-500 border border-red-500/30' :
                                                response.priority === 'P2' ? 'bg-orange-500/20 text-orange-500 border border-orange-500/30' :
                                                    response.priority === 'P3' ? 'bg-yellow-500/20 text-yellow-500 border border-yellow-500/30' :
                                                        'bg-green-500/20 text-green-500 border border-green-500/30'}`}>
                                            {response.priority}
                                        </span>
                                    </div>
                                </div>
                                <div>
                                    <span className="text-sm text-muted-foreground block mb-1">Type</span>
                                    <div>{response.incident_type}</div>
                                </div>
                                <div>
                                    <span className="text-sm text-muted-foreground block mb-1">Reasoning</span>
                                    <div className="text-sm text-muted-foreground leading-relaxed">{response.reasoning}</div>
                                </div>
                                {response.safety_checks && Object.keys(response.safety_checks).length > 0 && (
                                    <div className="mt-4 p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
                                        <div className="flex items-center gap-2 mb-1 text-green-500 font-semibold text-sm">
                                            <Shield size={16} />
                                            <span>Safety Checks Passed</span>
                                        </div>
                                        <div className="text-xs text-green-400/80">✅ Guardrails verified this response is safe</div>
                                    </div>
                                )}
                            </div>

                            {/* Status Message - Public View Only */}
                            <div className="mt-8 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg text-center">
                                <div className="font-bold text-blue-400 mb-1">Incident Reported Successfully</div>
                                <p className="text-sm text-blue-200/80">
                                    Your report has been sent to the command center.
                                    Dispatchers are reviewing your request and will assign assets shortly.
                                </p>
                            </div>

                            {/* Commander Info Display */}
                            {response.commander_info && (
                                <div className="mt-4 p-4 bg-card border border-border rounded-lg animate-in fade-in slide-in-from-bottom-2">
                                    <div className="flex items-center gap-3 mb-3">
                                        <div className="w-10 h-10 rounded-full bg-white text-black flex items-center justify-center">
                                            <Shield size={20} />
                                        </div>
                                        <div>
                                            <div className="font-bold text-sm">Commander Assigned</div>
                                            <div className="text-xs text-muted-foreground">Help is on the way</div>
                                        </div>
                                    </div>

                                    <div className="space-y-2 text-sm">
                                        <div className="flex justify-between items-center p-2 bg-secondary rounded">
                                            <span className="text-muted-foreground">Name</span>
                                            <span className="font-medium">{response.commander_info.name}</span>
                                        </div>
                                        <div className="flex justify-between items-center p-2 bg-secondary rounded">
                                            <span className="text-muted-foreground">Contact</span>
                                            <span className="font-medium font-mono">{response.commander_info.phone}</span>
                                        </div>
                                        {response.commander_info.zone && (
                                            <div className="flex justify-between items-center p-2 bg-secondary rounded">
                                                <span className="text-muted-foreground">Zone</span>
                                                <span className="font-medium">{response.commander_info.zone}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="bg-card border border-border rounded-xl p-12 text-center opacity-50 flex flex-col items-center justify-center h-full min-h-[300px]">
                            <AlertTriangle size={48} className="mb-4 opacity-30" />
                            <p className="text-muted-foreground">Submit an incident to see AI recommendations</p>
                        </div>
                    )}
                </div>
            </div>

            {/* --- Map Modal Overlay --- */}
            {isMapOpen && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-card border border-border rounded-xl w-full max-w-3xl overflow-hidden shadow-2xl">
                        <div className="p-4 flex justify-between items-center border-b border-border">
                            <h3 className="font-semibold">Select Location</h3>
                            <button onClick={() => setIsMapOpen(false)} className="text-muted-foreground hover:text-white"><XCircle size={24} /></button>
                        </div>
                        <div className="p-0">
                            {isLoaded ? (
                                <GoogleMap mapContainerStyle={mapContainerStyle} center={formData.latitude ? { lat: parseFloat(formData.latitude), lng: parseFloat(formData.longitude) } : defaultCenter} zoom={13} onClick={onMapClick}>
                                    {formData.latitude && formData.longitude && (
                                        <Marker
                                            position={{ lat: parseFloat(formData.latitude), lng: parseFloat(formData.longitude) }}
                                            draggable={true}
                                            onDragEnd={onMarkerDragEnd}
                                        />
                                    )}
                                </GoogleMap>
                            ) : <div className="p-8 text-center">Loading Map...</div>}
                        </div>
                        <div className="p-4 flex justify-end gap-4 items-center border-t border-border">
                            <div className="mr-auto text-sm text-muted-foreground">
                                Click on map or drag marker to set location
                            </div>
                            <button className="bg-white text-black font-bold px-6 py-2 rounded-lg hover:bg-gray-200" onClick={() => setIsMapOpen(false)}>Confirm Location</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default IncidentForm