import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/transcript_model.dart';
import '../services/audio_service.dart';
import '../services/auth_service.dart';
import '../services/websocket_service.dart';
import '../utils/constants.dart';

// ── Providers ────────────────────────────────────────────────────────────────

final authServiceProvider = Provider<AuthService>((_) => AuthService());

final webSocketServiceProvider = Provider<WebSocketService>((ref) {
  final auth = ref.read(authServiceProvider);
  return WebSocketService(auth);
});

final audioCaptureProvider = Provider<AudioCaptureService>((_) => AudioCaptureService());

final translatorProvider =
    StateNotifierProvider<TranslatorNotifier, TranslatorState>((ref) {
  return TranslatorNotifier(
    ref.read(webSocketServiceProvider),
    ref.read(audioCaptureProvider),
  );
});

// ── State ─────────────────────────────────────────────────────────────────────

enum AppStatus { idle, listening, processing, error, reconnecting }

class TranslatorState {
  final AppStatus status;
  final List<SubtitleSegment> segments;       // committed (final) subtitles
  final String partialFr;                     // current in-progress line
  final String partialEn;
  final double? lastLatencyMs;
  final String? errorMessage;
  final WsState wsState;

  const TranslatorState({
    this.status = AppStatus.idle,
    this.segments = const [],
    this.partialFr = '',
    this.partialEn = '',
    this.lastLatencyMs,
    this.errorMessage,
    this.wsState = WsState.disconnected,
  });

  TranslatorState copyWith({
    AppStatus? status,
    List<SubtitleSegment>? segments,
    String? partialFr,
    String? partialEn,
    double? lastLatencyMs,
    String? errorMessage,
    WsState? wsState,
  }) =>
      TranslatorState(
        status: status ?? this.status,
        segments: segments ?? this.segments,
        partialFr: partialFr ?? this.partialFr,
        partialEn: partialEn ?? this.partialEn,
        lastLatencyMs: lastLatencyMs ?? this.lastLatencyMs,
        errorMessage: errorMessage ?? this.errorMessage,
        wsState: wsState ?? this.wsState,
      );
}

// ── Notifier ──────────────────────────────────────────────────────────────────

class TranslatorNotifier extends StateNotifier<TranslatorState> {
  final WebSocketService _ws;
  final AudioCaptureService _audio;

  StreamSubscription<TranscriptEvent>? _transcriptSub;
  StreamSubscription<WsState>? _stateSub;
  StreamSubscription<Uint8List>? _audioSub;

  TranslatorNotifier(this._ws, this._audio) : super(const TranslatorState()) {
    _stateSub = _ws.stateStream.listen(_onWsStateChange);
    _transcriptSub = _ws.transcriptStream.listen(_onTranscript);
  }

  // ── Start / Stop ──────────────────────────────────────────────────────────

  Future<void> startListening() async {
    state = state.copyWith(
      status: AppStatus.listening,
      segments: [],
      partialFr: '',
      partialEn: '',
      errorMessage: null,
    );

    await _ws.connect();

    // Pipe audio → WebSocket
    await _audio.start();
    _audioSub = _audio.audioStream.listen((chunk) {
      _ws.sendAudio(chunk);
    });
  }

  Future<void> stopListening() async {
    await _audioSub?.cancel();
    _audioSub = null;
    await _audio.stop();
    await _ws.disconnect();

    state = state.copyWith(
      status: AppStatus.idle,
      partialFr: '',
      partialEn: '',
    );
  }

  // ── Event Handlers ────────────────────────────────────────────────────────

  void _onTranscript(TranscriptEvent event) {
    state = state.copyWith(status: AppStatus.processing);

    if (event.isPartial) {
      state = state.copyWith(
        partialFr: event.translationFr,
        partialEn: event.transcriptEn,
        lastLatencyMs: event.totalLatencyMs,
      );
    } else {
      // Final → commit segment, clear partial
      final newSegment = SubtitleSegment(
        textFr: event.translationFr,
        textEn: event.transcriptEn,
        latencyMs: event.totalLatencyMs,
      );

      var newSegments = [...state.segments, newSegment];
      if (newSegments.length > AppConstants.maxDisplayedSegments) {
        newSegments = newSegments.sublist(
          newSegments.length - AppConstants.maxDisplayedSegments,
        );
      }

      state = state.copyWith(
        segments: newSegments,
        partialFr: '',
        partialEn: '',
        status: AppStatus.listening,
        lastLatencyMs: event.totalLatencyMs,
      );
    }
  }

  void _onWsStateChange(WsState wsState) {
    AppStatus appStatus;
    switch (wsState) {
      case WsState.connected:
        appStatus = AppStatus.listening;
      case WsState.reconnecting:
        appStatus = AppStatus.reconnecting;
      case WsState.error:
        appStatus = AppStatus.error;
      default:
        appStatus = AppStatus.idle;
    }
    state = state.copyWith(wsState: wsState, status: appStatus);
  }

  @override
  void dispose() {
    _transcriptSub?.cancel();
    _stateSub?.cancel();
    _audioSub?.cancel();
    _ws.dispose();
    _audio.dispose();
    super.dispose();
  }
}
