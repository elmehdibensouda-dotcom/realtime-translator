/**
 * Helper to capture raw audio from the mic, downsample to 16kHz,
 * and convert to Int16 PCM for the backend.
 */
export class AudioStreamer {
  constructor(onChunk) {
    this.onChunk = onChunk;
    this.audioContext = null;
    this.stream = null;
    this.processor = null;
  }

  async start() {
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 16000,
    });

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    const source = this.audioContext.createMediaStreamSource(this.stream);
    
    // 4096 buffer size is safe for most browsers
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

    this.processor.onaudioprocess = (e) => {
      const inputData = e.inputBuffer.getChannelData(0);
      const pcmData = this.floatTo16BitPCM(inputData);
      this.onChunk(pcmData);
    };

    source.connect(this.processor);
    this.processor.connect(this.audioContext.destination);
  }

  stop() {
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }

  /**
   * Converts Float32Array (web audio) to Int16Array (PCM).
   */
  floatTo16BitPCM(input) {
    const output = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
      const s = Math.max(-1, Math.min(1, input[i]));
      output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return output.buffer;
  }
}
