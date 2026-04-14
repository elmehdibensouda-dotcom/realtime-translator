import 'dart:convert';
import 'dart:typed_data';

/// Types of events received from the backend WebSocket.
enum TranscriptType { partial, final_ }

/// A single transcript + translation event from the backend.
class TranscriptEvent {
  final TranscriptType type;
  final String sessionId;
  final int sequence;
  final String transcriptEn;
  final double confidence;
  final String translationFr;
  final double? asrLatencyMs;
  final double? translationLatencyMs;
  final double? totalLatencyMs;
  final double serverTs;

  const TranscriptEvent({
    required this.type,
    required this.sessionId,
    required this.sequence,
    required this.transcriptEn,
    required this.confidence,
    required this.translationFr,
    this.asrLatencyMs,
    this.translationLatencyMs,
    this.totalLatencyMs,
    required this.serverTs,
  });

  factory TranscriptEvent.fromJson(Map<String, dynamic> json) {
    return TranscriptEvent(
      type: json['type'] == 'final' ? TranscriptType.final_ : TranscriptType.partial,
      sessionId: json['session_id'] as String? ?? '',
      sequence: (json['sequence'] as num?)?.toInt() ?? 0,
      transcriptEn: json['transcript_en'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      translationFr: json['translation_fr'] as String? ?? '',
      asrLatencyMs: (json['asr_latency_ms'] as num?)?.toDouble(),
      translationLatencyMs: (json['translation_latency_ms'] as num?)?.toDouble(),
      totalLatencyMs: (json['total_latency_ms'] as num?)?.toDouble(),
      serverTs: (json['server_ts'] as num?)?.toDouble() ?? 0.0,
    );
  }

  bool get isFinal => type == TranscriptType.final_;
  bool get isPartial => type == TranscriptType.partial;
}

/// A committed subtitle segment (always final).
class SubtitleSegment {
  final String textFr;
  final String textEn;
  final double? latencyMs;
  final DateTime createdAt;

  SubtitleSegment({
    required this.textFr,
    required this.textEn,
    this.latencyMs,
  }) : createdAt = DateTime.now();
}
