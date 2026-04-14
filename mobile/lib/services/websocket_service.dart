import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:logger/logger.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../models/transcript_model.dart';
import '../utils/constants.dart';
import 'auth_service.dart';

final _logger = Logger(printer: PrettyPrinter(methodCount: 0));

enum WsState { disconnected, connecting, connected, reconnecting, error }

/// Manages the WebSocket lifecycle: connect, send audio, receive events.
///
/// Emits [TranscriptEvent] objects via [transcriptStream].
/// Emits [WsState] changes via [stateStream].
class WebSocketService {
  final AuthService _authService;

  WebSocketService(this._authService);

  IOWebSocketChannel? _channel;
  StreamSubscription? _subscription;
  Timer? _pingTimer;
  Timer? _reconnectTimer;

  final _transcriptController = StreamController<TranscriptEvent>.broadcast();
  final _stateController = StreamController<WsState>.broadcast();

  Stream<TranscriptEvent> get transcriptStream => _transcriptController.stream;
  Stream<WsState> get stateStream => _stateController.stream;

  WsState _state = WsState.disconnected;
  int _reconnectAttempts = 0;
  String? _sessionId;
  bool _intentionalClose = false;

  WsState get state => _state;
  String? get sessionId => _sessionId;

  // ── Connect ─────────────────────────────────────────────────────────────

  Future<void> connect() async {
    _intentionalClose = false;
    _setState(WsState.connecting);

    String token;
    try {
      token = await _authService.getToken();
    } catch (e) {
      _logger.e('Auth failed: $e');
      _setState(WsState.error);
      return;
    }

    final uri = Uri.parse('${AppConstants.wsBaseUrl}?token=$token');
    _logger.i('Connecting to $uri');

    try {
      _channel = IOWebSocketChannel.connect(
        uri,
        connectTimeout: AppConstants.wsConnectTimeout,
        pingInterval: AppConstants.wsPingInterval,
      );

      _subscription = _channel!.stream.listen(
        _onMessage,
        onError: _onError,
        onDone: _onDone,
      );

      _reconnectAttempts = 0;
      _setState(WsState.connected);
      _logger.i('WebSocket connected');
    } catch (e) {
      _logger.e('WebSocket connect error: $e');
      _scheduleReconnect();
    }
  }

  // ── Send audio ───────────────────────────────────────────────────────────

  void sendAudio(Uint8List bytes) {
    if (_state == WsState.connected && _channel != null) {
      try {
        _channel!.sink.add(bytes);
      } catch (e) {
        _logger.w('Send error: $e');
      }
    }
  }

  // ── Receive ──────────────────────────────────────────────────────────────

  void _onMessage(dynamic message) {
    try {
      final json = jsonDecode(message as String) as Map<String, dynamic>;

      // Status event (connected / reconnecting / disconnected)
      if (json.containsKey('event')) {
        final event = json['event'] as String;
        _sessionId = json['session_id'] as String?;
        _logger.d('Status event: $event (session=$_sessionId)');
        return;
      }

      // Transcript event
      if (json.containsKey('transcript_en')) {
        final event = TranscriptEvent.fromJson(json);
        _transcriptController.add(event);
      }
    } catch (e) {
      _logger.w('Failed to parse WS message: $e');
    }
  }

  void _onError(Object error) {
    _logger.e('WebSocket error: $error');
    _setState(WsState.error);
    if (!_intentionalClose) _scheduleReconnect();
  }

  void _onDone() {
    _logger.i('WebSocket closed');
    if (!_intentionalClose) _scheduleReconnect();
  }

  // ── Reconnect (exponential backoff) ──────────────────────────────────────

  void _scheduleReconnect() {
    if (_intentionalClose) return;
    if (_reconnectAttempts >= AppConstants.wsMaxReconnectAttempts) {
      _logger.e('Max reconnect attempts reached');
      _setState(WsState.error);
      return;
    }

    _setState(WsState.reconnecting);
    _reconnectAttempts++;
    final delay = AppConstants.wsReconnectBaseDelay * (1 << _reconnectAttempts);
    _logger.i('Reconnecting in ${delay.inMilliseconds}ms (attempt $_reconnectAttempts)');

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(delay, connect);
  }

  // ── Disconnect ───────────────────────────────────────────────────────────

  Future<void> disconnect() async {
    _intentionalClose = true;
    _reconnectTimer?.cancel();
    _pingTimer?.cancel();
    await _subscription?.cancel();
    await _channel?.sink.close();
    _channel = null;
    _setState(WsState.disconnected);
    _logger.i('WebSocket disconnected');
  }

  void _setState(WsState newState) {
    _state = newState;
    _stateController.add(newState);
  }

  Future<void> dispose() async {
    await disconnect();
    await _transcriptController.close();
    await _stateController.close();
  }
}
