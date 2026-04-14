import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Square, Translate, Globe, Activity, Zap, AlertCircle } from 'lucide-react';
import { AudioStreamer } from './utils/audioStreamer';

const WS_URL = 'ws://localhost:8001/ws/translate';
const AUTH_URL = 'http://localhost:8001/auth/token';

export default function App() {
  const [status, setStatus] = useState('idle'); // idle | listening | processing | error
  const [segments, setSegments] = useState([]);
  const [partial, setPartial] = useState({ en: '', fr: '' });
  const [latency, setLatency] = useState(null);
  const [error, setError] = useState(null);
  
  const wsRef = useRef(null);
  const streamerRef = useRef(null);
  const scrollRef = useRef(null);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [segments, partial]);

  const startListening = async () => {
    try {
      setError(null);
      setStatus('connecting');

      // 1. Get Auth Token
      const authRes = await fetch(AUTH_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: 'web-client-' + Math.random().toString(36).substring(7) })
      });
      const { access_token } = await authRes.json();

      // 2. Connect WebSocket
      const ws = new WebSocket(`${WS_URL}?token=${access_token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus('listening');
        // 3. Start Audio Streamer
        streamerRef.current = new AudioStreamer((chunk) => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(chunk);
          }
        });
        streamerRef.current.start();
      };

      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.event === 'connected') return;

        if (data.type === 'final') {
          setSegments(prev => [...prev, { en: data.transcript_en, fr: data.translation_fr, id: Date.now() }].slice(-10));
          setPartial({ en: '', fr: '' });
          setStatus('listening');
        } else {
          setPartial({ en: data.transcript_en, fr: data.translation_fr });
          setStatus('processing');
        }
        if (data.total_latency_ms) setLatency(data.total_latency_ms);
      };

      ws.onerror = (err) => {
        console.error('WS Error:', err);
        setError('Connection error');
        stopListening();
      };

      ws.onclose = () => {
        if (status !== 'idle') setStatus('idle');
      };

    } catch (err) {
      console.error(err);
      setError(err.message);
      setStatus('error');
    }
  };

  const stopListening = () => {
    if (streamerRef.current) streamerRef.current.stop();
    if (wsRef.current) wsRef.current.close();
    setStatus('idle');
    setPartial({ en: '', fr: '' });
  };

  return (
    <div className="flex flex-col h-screen max-w-2xl mx-auto px-4 py-8">
      {/* Header */}
      <header className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center glow">
            <Globe className="text-white w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold">Live Translator</h1>
            <p className="text-xs text-white/40 uppercase tracking-widest">English → French</p>
          </div>
        </div>
        
        {latency && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-indigo-500/10 border border-indigo-500/20 rounded-full">
            <Zap className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-xs font-semibold text-indigo-300">{Math.round(latency)} ms</span>
          </div>
        )}
      </header>

      {/* Main Container */}
      <main className="flex-1 flex flex-col bg-[#161621] rounded-3xl border border-white/5 overflow-hidden mb-8">
        {/* Status Bar */}
        <div className="flex items-center justify-center py-4 bg-white/[0.02] border-b border-white/5">
          <div className={`flex items-center gap-2 px-4 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
            status === 'listening' ? 'text-emerald-400 bg-emerald-400/10' :
            status === 'processing' ? 'text-indigo-400 bg-indigo-400/10' :
            status === 'connecting' ? 'text-amber-400 bg-amber-400/10' :
            'text-white/20 bg-white/5'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              status === 'listening' ? 'bg-emerald-400 pulsing' :
              status === 'processing' ? 'bg-indigo-400 pulsing' :
              status === 'connecting' ? 'bg-amber-400 animate-pulse' :
              'bg-white/20'
            }`} />
            {status}
          </div>
        </div>

        {/* Subtitles Area */}
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth"
        >
          {segments.length === 0 && !partial.en && (
            <div className="h-full flex flex-col items-center justify-center text-white/10 italic">
              <Mic className="w-12 h-12 mb-4 opacity-10" />
              <p>Click start and begin speaking</p>
            </div>
          )}

          <AnimatePresence>
            {segments.map((s) => (
              <motion.div 
                key={s.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-1.5"
              >
                <p className="text-lg font-medium text-white/90 leading-tight">
                  {s.fr}
                </p>
                <p className="text-sm italic text-white/30">
                  {s.en}
                </p>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Partial result */}
          {partial.en && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="bg-indigo-500/5 border border-indigo-500/10 p-4 rounded-2xl relative"
            >
              <div className="absolute top-4 -left-1 w-1 h-6 bg-indigo-500 rounded-full" />
              <p className="text-lg font-medium text-indigo-100/80 leading-tight">
                {partial.fr}
              </p>
              <p className="text-sm italic text-white/20 mt-1">
                {partial.en}
              </p>
            </motion.div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="mx-6 mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center gap-3 text-red-400 text-sm">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p>{error}</p>
          </div>
        )}
      </main>

      {/* Control Button */}
      <div className="flex justify-center pb-4">
        <button
          onClick={status === 'idle' || status === 'error' ? startListening : stopListening}
          disabled={status === 'connecting'}
          className={`group flex items-center gap-3 px-8 py-5 rounded-3xl transition-all duration-300 font-bold text-lg ${
            status === 'idle' || status === 'error'
            ? 'bg-indigo-600 hover:bg-indigo-500 shadow-indigo-500/40' 
            : 'bg-red-600 hover:bg-red-500 shadow-red-500/40'
          } shadow-xl hover:-translate-y-1 disabled:opacity-50 disabled:translate-y-0`}
        >
          {status === 'idle' || status === 'error' ? (
            <>
              <Mic className="w-6 h-6" />
              <span>Start Translating</span>
            </>
          ) : (
            <>
              <Square className="w-6 h-6 fill-current" />
              <span>Stop</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
