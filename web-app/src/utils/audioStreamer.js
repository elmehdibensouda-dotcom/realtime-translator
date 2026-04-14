/**
 * Robust Audio capture utility with downsampling to 16kHz for AssemblyAI compatibility.
 */
export class AudioStreamer {
  constructor(onChunk) {
    this.onChunk = onChunk;
    this.audioContext = null;
    this.stream = null;
    this.processor = null;
  }

  async start() {
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const sourceSampleRate = this.audioContext.sampleRate;
    console.log('Original Sample Rate:', sourceSampleRate);

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    const source = this.audioContext.createMediaStreamSource(this.stream);
    
    // We use a large buffer initially to avoid drops
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

    this.processor.onaudioprocess = (e) => {
      const inputData = e.inputBuffer.getChannelData(0);
      
      // DOWNSAMPLE to 16kHz
      const downsampledBuffer = this.downsampleBuffer(inputData, sourceSampleRate, 16000);
      const pcmData = this.floatTo16BitPCM(downsampledBuffer);
      
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
   * Resamples raw audio to target sample rate.
   */
  downsampleBuffer(buffer, sampleRate, outSampleRate) {
    if (outSampleRate === sampleRate) return buffer;
    if (outSampleRate > sampleRate) {
      console.warn('Upsampling not supported properly');
      return buffer;
    }
    
    const sampleRateRatio = sampleRate / outSampleRate;
    const newLength = Math.round(buffer.length / sampleRateRatio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
      let accum = 0;
      let count = 0;
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
        accum += buffer[i];
        count++;
      }
      result[offsetResult] = accum / count;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }
    return result;
  }

  /**
   * Converts Float32Array to Int16Array (PCM).
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
