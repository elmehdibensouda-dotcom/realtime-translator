import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Square, Languages, AlertCircle, Activity, Zap, RefreshCw } from 'lucide-react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/translate';
const AUTH_URL = import.meta.env.VITE_AUTH_URL || 'http://localhost:8000/auth/token';

export default function App() {
  const [status, setStatus] = useState('idle'); // idle | connecting | listening | reconnecting | error
  const [segments, setSegments] = useState([]);
  const [liveEn, setLiveEn] = useState('');
  const [liveFr, setLiveFr] = useState('');
  const [error, setError] = useState(null);
  const [fontSize, setFontSize] = useState(52);
  
  const wsRef = useRef(null);
  const recognitionRef = useRef(null);
  const scrollRef = useRef(null);
  const lastTranslatedText = useRef('');
  const lastSeqRef = useRef(0);
  const retryCount = useRef(0);
  const maxRetries = 5;

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [segments, liveEn]);

  const requestTranslation = useCallback((text, is_final) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !text.trim()) return;
    
    const wordCount = text.split(' ').length;
    const lastWordCount = lastTranslatedText.current.split(' ').length;
    
    if (!is_final && (wordCount - lastWordCount) < 4) return;

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
        body: JSON.stringify({ client_id: 'prod-web-' + Math.random().toString(36).substring(7) }),
      });
      const { access_token } = await authRes.json();

      const ws = new WebSocket(`${WS_URL}?token=${access_token}`);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.seq_id && data.seq_id < lastSeqRef.current && data.type !== 'final') return;

        if (data.type === 'final') {
          setSegments(prev => [...prev, { en: data.transcript_en, fr: data.translation_fr, id: Date.now() }].slice(-30));
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

      ws.onerror = () => {
         // L'erreur sera gérée par onclose
      };

    } catch (err) {
      setError("Erreur de connexion au serveur.");
      setStatus('error');
    }
  }, [status]);

  const handleReconnect = () => {
    if (retryCount.current < maxRetries) {
      setStatus('reconnecting');
      retryCount.current++;
      setTimeout(connectWS, 2000 * retryCount.current); // Backoff exponentiel
    } else {
      setStatus('error');
      setError("Connexion perdue. Merci de rafraîchir la page.");
    }
  };

  const startListening = async () => {
    try {
      setError(null);
      setStatus('connecting');
      await connectWS();

      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.lang = 'en-US';
      recognition.continuous = true;
      recognition.interimResults = true;
      recognitionRef.current = recognition;

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

      recognition.onend = () => { 
        if (recognitionRef.current) recognition.start(); 
      };

      recognition.start();

    } catch (err) {
      setError(err.message);
      setStatus('error');
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

  return (
    <div className="flex flex-col h-screen bg-black text-white font-sans overflow-hidden">
      <header className="px-10 py-6 border-b border-white/10 flex justify-between items-center bg-[#050505] shrink-0">
        <div className="flex items-center gap-4">
          {status === 'reconnecting' ? (
            <RefreshCw className="text-amber-500 w-6 h-6 animate-spin" />
          ) : (
            <Zap className="text-indigo-500 fill-indigo-500 w-6 h-6" />
          )}
          <h1 className="text-xl font-black uppercase tracking-tighter">
            {status === 'reconnecting' ? 'Reconnect...' : 'TurboTranslator'}
          </h1>
        </div>
        <div className="flex gap-2">
           <button onClick={() => setFontSize(f => f-4)} className="p-3 bg-white/5 rounded-xl hover:bg-white/10 transition-colors"><Minus className="w-5 h-5" /></button>
           <button onClick={() => setFontSize(f => f+4)} className="p-3 bg-white/5 rounded-xl hover:bg-white/10 transition-colors"><Plus className="w-5 h-5" /></button>
        </div>
      </header>

      <main ref={scrollRef} className="flex-1 overflow-y-auto px-10 py-10 space-y-12 scroll-smooth no-scrollbar">
        {segments.map((s) => (
          <div key={s.id} className="opacity-20 space-y-3 pl-8 relative">
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-white/10 rounded-full" />
            <p className="font-bold leading-tight" style={{ fontSize: `${fontSize*0.65}px` }}>{s.fr}</p>
            <p className="text-sm opacity-60 italic">{s.en}</p>
          </div>
        ))}

        {liveEn && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-5 duration-300">
            <p className="font-black text-indigo-400 leading-[1.1] tracking-tight" style={{ fontSize: `${fontSize}px` }}>
               {liveFr || '...'}
            </p>
            <div className="flex items-center gap-3 text-white/40">
               <Activity className="w-5 h-5 animate-pulse" />
               <p className="text-xl italic font-medium">{liveEn}</p>
            </div>
          </div>
        )}

        {!liveEn && segments.length === 0 && (
           <div className="h-full flex flex-col items-center justify-center opacity-5 text-center transform -translate-y-10">
              <Mic className="w-48 h-48 mb-6" />
              <p className="text-4xl font-extrabold uppercase tracking-widest">Awaiting Voice</p>
           </div>
        )}
        <div className="h-20" />
      </main>

      <footer className="p-12 bg-[#050505] flex justify-center border-t border-white/10 shrink-0">
        <button
          onClick={status === 'listening' ? stopListening : startListening}
          className={`px-20 py-7 rounded-[2rem] font-black text-2xl transition-all shadow-2xl active:scale-95 ${
            status === 'listening' || status === 'reconnecting' 
            ? 'bg-red-600/20 text-red-500 border-2 border-red-500/50' 
            : 'bg-indigo-600 text-white shadow-indigo-600/30'
          }`}
        >
          {status === 'reconnecting' ? 'RECONNECTING...' : status === 'listening' ? 'STOP' : 'START SESSION'}
        </button>
      </footer>

      {error && (
        <div className="absolute top-24 left-10 right-10 p-5 bg-red-600 rounded-2xl flex items-center gap-4 shadow-2xl animate-in slide-in-from-top-10">
          <AlertCircle className="w-6 h-6" />
          <p className="font-bold">{error}</p>
        </div>
      )}

      <style>{`
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
      `}</style>
    </div>
  );
}

function Plus(props) { return <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>; }
function Minus(props) { return <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line></svg>; }
