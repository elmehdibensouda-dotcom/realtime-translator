import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Square, Languages, AlertCircle, Activity, Zap, RefreshCw, Volume2, Settings2, Trash2, Maximize2, ChevronDown } from 'lucide-react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/translate';
const AUTH_URL = import.meta.env.VITE_AUTH_URL || 'http://localhost:8000/auth/token';

export default function App() {
  const [status, setStatus] = useState('idle'); // idle | connecting | listening | reconnecting | error
  const [segments, setSegments] = useState([]);
  const [liveEn, setLiveEn] = useState('');
  const [liveFr, setLiveFr] = useState('');
  const [error, setError] = useState(null);
  const [fontSize, setFontSize] = useState(48);
  const [isAutoScroll, setIsAutoScroll] = useState(true);
  
  const wsRef = useRef(null);
  const recognitionRef = useRef(null);
  const scrollRef = useRef(null);
  const lastTranslatedText = useRef('');
  const lastSeqRef = useRef(0);
  const retryCount = useRef(0);
  const maxRetries = 5;

  // Optimized smooth scroll
  useEffect(() => {
    if (isAutoScroll && scrollRef.current) {
      const target = scrollRef.current;
      target.scrollTo({ top: target.scrollHeight, behavior: 'smooth' });
    }
  }, [segments, liveEn, isAutoScroll]);

  const requestTranslation = useCallback((text, is_final) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !text.trim()) return;
    
    const wordCount = text.split(' ').length;
    const lastWordCount = lastTranslatedText.current.split(' ').length;
    
    // Throttle interim updates – lowered to 2 words for maximum responsiveness
    if (!is_final && (wordCount - lastWordCount) < 2) return;

    lastTranslatedText.current = text;
    const seqId = ++lastSeqRef.current;
    
    ws.send(JSON.stringify({ 
      text: text.trim(), 
      is_final,
      seq_id: seqId 
    }));
  }, []);

  const connectWS = useCallback(async () => {
    try {
      const authRes = await fetch(AUTH_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: 'turbo-web-' + Math.random().toString(36).substring(7) }),
      });
      if (!authRes.ok) throw new Error("Auth failed");
      const { access_token } = await authRes.json();

      const ws = new WebSocket(`${WS_URL}?token=${access_token}`);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        // Ignore late seq results if a newer one already arrived for partials
        if (data.seq_id && data.seq_id < lastSeqRef.current && data.type !== 'final') return;

        if (data.type === 'final') {
          setSegments(prev => [...prev, { en: data.transcript_en, fr: data.translation_fr, id: Date.now() }].slice(-50));
          setLiveEn('');
          setLiveFr('');
          lastTranslatedText.current = '';
        } else {
          setLiveFr(data.translation_fr || '');
        }
      };

      ws.onopen = () => {
        setStatus('listening');
        retryCount.current = 0;
        setError(null);
      };

      ws.onclose = () => {
        if (status === 'listening' || status === 'reconnecting') {
          handleReconnect();
        } else {
          setStatus('idle');
        }
      };

      ws.onerror = () => { /* Handled by onclose */ };

    } catch (err) {
      console.error("Connection error:", err);
      setError(`Connection failed: ${err.message}. Ensure backend is live at ${WS_URL}`);
      setStatus('error');
    }
  }, [status]);

  const handleReconnect = () => {
    if (retryCount.current < maxRetries) {
      setStatus('reconnecting');
      retryCount.current++;
      setTimeout(connectWS, 2000 * retryCount.current);
    } else {
      setStatus('error');
      setError("Connection lost. Please check your internet and refresh.");
    }
  };

  const startListening = async () => {
    try {
      setError(null);
      setStatus('connecting');

      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        throw new Error("Speech Recognition not supported in this browser. Try Chrome.");
      }

      const recognition = new SpeechRecognition();
      recognition.lang = 'en-US';
      recognition.continuous = true;
      recognition.interimResults = true;
      recognitionRef.current = recognition;

      recognition.onstart = () => {
        console.log("Speech recognition started");
        setStatus('listening');
      };

      recognition.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) {
            requestTranslation(result[0].transcript, true);
          } else {
            interim += result[0].transcript;
          }
        }
        if (interim) {
          setLiveEn(interim);
          requestTranslation(interim, false);
        }
      };

      recognition.onerror = (e) => {
         console.error("Speech Recognition Error:", e.error);
         if (e.error === 'not-allowed') setError("Microphone access denied. Please enable it in browser settings.");
         else if (e.error === 'network') setError("Network error affecting speech recognition.");
         else setError(`Speech error: ${e.error}`);
         setStatus('error');
         stopListening();
      };

      recognition.onend = () => { 
        if (recognitionRef.current) {
          console.log("Speech recognition ended unexpectedly, restarting...");
          recognition.start(); 
        }
      };

      // START RECOGNITION IMMEDIATELY (prevents browser security block)
      recognition.start();

      // THEN CONNECT TO SERVER
      await connectWS();

    } catch (err) {
      console.error("Start error:", err);
      setError(err.message);
      setStatus('error');
      stopListening();
    }
  };

  const stopListening = () => {
    const rec = recognitionRef.current;
    recognitionRef.current = null;
    if (rec) { rec.onend = null; rec.stop(); }
    if (wsRef.current) wsRef.current.close();
    setStatus('idle');
    setLiveEn('');
    setLiveFr('');
  };

  const clearHistory = () => {
    if (confirm("Clear all translation history?")) setSegments([]);
  };

  return (
    <div className="flex flex-col h-screen bg-[#050505] text-zinc-100 font-sans overflow-hidden selection:bg-indigo-500/30">
      {/* Dynamic Background Effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-20">
         <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/30 blur-[120px] rounded-full animate-pulse" />
         <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-600/20 blur-[120px] rounded-full" />
      </div>

      <header className="relative z-10 px-8 py-5 flex justify-between items-center border-b border-white/5 bg-black/40 backdrop-blur-xl shrink-0">
        <div className="flex items-center gap-4">
          <div className="relative">
            {status === 'listening' && (
              <span className="absolute -inset-1 bg-indigo-500 rounded-full blur opacity-40 animate-pulse" />
            )}
            <div className={`p-2 rounded-lg ${status === 'listening' ? 'bg-indigo-600' : 'bg-zinc-800'}`}>
               <Zap className={`w-5 h-5 ${status === 'listening' ? 'fill-white' : ''}`} />
            </div>
          </div>
          <div>
            <h1 className="text-lg font-black tracking-tighter uppercase leading-none">Turbo Translator</h1>
            <p className="text-[10px] text-zinc-500 font-bold tracking-widest uppercase mt-1">EN → FR • High-Speed Engine</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
           <button onClick={clearHistory} className="p-2.5 text-zinc-500 hover:text-red-400 hover:bg-red-400/10 rounded-xl transition-all" title="Clear History">
              <Trash2 className="w-5 h-5" />
           </button>
           <div className="h-6 w-px bg-white/10 mx-1" />
           <div className="flex p-1 bg-white/5 rounded-xl border border-white/5">
              <button onClick={() => setFontSize(f => Math.max(24, f-4))} className="px-3 py-1.5 hover:bg-white/5 rounded-lg transition-colors text-xs font-bold">A-</button>
              <button onClick={() => setFontSize(f => Math.min(100, f+4))} className="px-3 py-1.5 hover:bg-white/5 rounded-lg transition-colors text-xs font-bold">A+</button>
           </div>
        </div>
      </header>

      <main 
        ref={scrollRef} 
        onScroll={(e) => {
          const isAtBottom = e.target.scrollHeight - e.target.scrollTop <= e.target.clientHeight + 100;
          setIsAutoScroll(isAtBottom);
        }}
        className="relative z-10 flex-1 overflow-y-auto px-8 py-10 space-y-16 no-scrollbar custom-scroll-area"
      >
        <AnimatePresence initial={false}>
          {segments.map((s) => (
            <motion.div 
              key={s.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 0.25, y: 0 }}
              transition={{ duration: 0.4 }}
              className="group space-y-4 pl-10 relative hover:opacity-100 transition-opacity"
            >
              <div className="absolute left-0 top-2 bottom-2 w-1.5 bg-zinc-800 rounded-full group-hover:bg-indigo-600 transition-colors" />
              <p className="font-bold leading-tight tracking-tight text-white" style={{ fontSize: `${fontSize*0.65}px` }}>
                {s.fr}
              </p>
              <div className="flex items-center gap-3 opacity-60">
                 <Languages className="w-4 h-4" />
                 <p className="text-base font-medium italic">{s.en}</p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {liveEn && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-8 pb-32"
          >
            <div className="space-y-4">
               <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-black uppercase tracking-widest">
                  <Activity className="w-3 h-3 animate-pulse" />
                  Live Translation
               </div>
               <p className="font-black text-indigo-100 leading-[1.05] tracking-tight selection:bg-indigo-500" style={{ fontSize: `${fontSize}px` }}>
                  {liveFr || 'Thinking...'}
               </p>
            </div>
            
            <div className="flex items-start gap-4 p-6 bg-white/5 rounded-3xl border border-white/5 backdrop-blur-md">
               <div className="p-3 bg-white/10 rounded-2xl">
                  <Volume2 className="w-6 h-6 text-indigo-400" />
               </div>
               <div className="flex-1">
                  <p className="text-[10px] uppercase font-black tracking-widest text-zinc-500 mb-1">Source Audio (EN)</p>
                  <p className="text-xl font-semibold text-zinc-300 leading-relaxed italic">"{liveEn}"</p>
               </div>
            </div>
          </motion.div>
        )}

        {!liveEn && segments.length === 0 && (
           <div className="h-full flex flex-col items-center justify-center opacity-10 text-center py-20">
              <div className="relative mb-8">
                 <Mic className="w-32 h-32" />
                 <div className="absolute inset-0 bg-white blur-[60px] opacity-20 rounded-full" />
              </div>
              <p className="text-3xl font-black uppercase tracking-[0.2em] mb-2">Awaiting Session</p>
              <p className="text-sm font-bold tracking-widest uppercase opacity-50">Press Start to begin real-time translation</p>
           </div>
        )}
        
        {!isAutoScroll && segments.length > 0 && (
           <button 
             onClick={() => setIsAutoScroll(true)}
             className="fixed bottom-32 left-1/2 -translate-x-1/2 z-20 px-6 py-3 bg-white text-black font-black text-xs uppercase tracking-widest rounded-full shadow-2xl flex items-center gap-2 animate-bounce hover:scale-105 transition-transform"
           >
             <ChevronDown className="w-4 h-4" />
             New Content Below
           </button>
        )}
      </main>

      <footer className="relative z-20 p-8 pt-4 bg-gradient-to-t from-black via-black/95 to-transparent border-t border-white/5 shrink-0">
        <div className="max-w-xl mx-auto flex flex-col items-center gap-6">
           <div className="flex items-center gap-8 py-2">
              <div className="flex flex-col items-center gap-1 opacity-40">
                 <span className="text-[8px] font-black uppercase tracking-widest">Latency</span>
                 <span className="text-xs font-mono font-bold">~240ms</span>
              </div>
              <div className="w-px h-6 bg-white/10" />
              <div className="flex flex-col items-center gap-1 opacity-40">
                 <span className="text-[8px] font-black uppercase tracking-widest">Model</span>
                 <span className="text-xs font-mono font-bold">Turbo-V1</span>
              </div>
              <div className="w-px h-6 bg-white/10" />
              <div className="flex flex-col items-center gap-1 opacity-40">
                 <span className="text-[8px] font-black uppercase tracking-widest">Status</span>
                 <span className="text-xs font-mono font-bold uppercase">{status}</span>
              </div>
           </div>

           <button
             onClick={status === 'listening' || status === 'reconnecting' ? stopListening : startListening}
             disabled={status === 'connecting'}
             className={`group relative overflow-hidden px-14 py-6 rounded-[2.5rem] font-black text-xl tracking-widest uppercase transition-all shadow-2xl active:scale-95 disabled:opacity-50 ${
               status === 'listening' || status === 'reconnecting' 
               ? 'bg-red-500/10 text-red-500 border-2 border-red-500/50 hover:bg-red-500/20' 
               : 'bg-indigo-600 text-white hover:bg-indigo-500 shadow-indigo-600/40 hover:shadow-indigo-600/60'
             }`}
           >
             <div className="relative z-10 flex items-center gap-4">
               {status === 'connecting' ? (
                 <RefreshCw className="w-6 h-6 animate-spin" />
               ) : status === 'listening' ? (
                 <Square className="w-6 h-6 fill-current" />
               ) : (
                 <Mic className="w-6 h-6" />
               )}
               <span>
                 {status === 'connecting' ? 'Initializing...' : 
                  status === 'reconnecting' ? 'Restoring...' :
                  status === 'listening' ? 'Finish Session' : 'Start Translation'}
               </span>
             </div>
             {status !== 'listening' && (
                <div className="absolute top-0 -inset-full h-full w-1/2 z-5 block transform -skew-x-12 bg-gradient-to-r from-transparent to-white/20 opacity-40 group-hover:animate-shine" />
             )}
           </button>
           
           <p className="text-[10px] text-zinc-600 font-bold uppercase tracking-widest">
             Powered by WebSpeech & TurboCore Integration
           </p>
        </div>
      </footer>

      {error && (
        <motion.div 
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute top-24 left-8 right-8 z-50 p-5 bg-red-600 rounded-2xl flex items-center justify-between gap-4 shadow-[0_20px_50px_rgba(220,38,38,0.3)] border border-white/20"
        >
          <div className="flex items-center gap-4">
             <AlertCircle className="w-6 h-6" />
             <p className="font-bold text-sm tracking-tight">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="p-2 hover:bg-white/10 rounded-lg">
             <Square className="w-4 h-4 rotate-45" />
          </button>
        </motion.div>
      )}

      <style>{`
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        
        @keyframes shine {
          0% { left: -100%; }
          100% { left: 100%; }
        }
        .animate-shine {
          animation: shine 1.5s infinite;
        }
        
        .custom-scroll-area {
          scrollbar-gutter: stable;
        }

        @media (max-width: 640px) {
           header { px-4 py-4; }
           main { px-4 py-6; space-y-10; }
           footer { p-6; }
           .px-14 { px-10; }
        }
      `}</style>
    </div>
  );
}
