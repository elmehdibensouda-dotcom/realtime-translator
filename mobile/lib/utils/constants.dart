/// App-wide constants — update WS_BASE_URL for your deployment.
library;

class AppConstants {
  AppConstants._();

  // ── Backend ──────────────────────────────────────────────────────────────
  // Note: Use 10.0.2.2 for Android Emulator, localhost for iOS Simulator
  static const String wsBaseUrl = 'ws://localhost:8080/ws/translate';
  static const String apiBaseUrl = 'http://localhost:8080';
  static const String authTokenEndpoint = '/auth/token';

  // ── Audio ────────────────────────────────────────────────────────────────
  static const int sampleRate = 16000;
  static const int channels = 1;
  static const int bitDepth = 16;
  static const int chunkMs = 100; // ms per audio frame sent over WS

  // ── WebSocket ─────────────────────────────────────────────────────────────
  static const Duration wsConnectTimeout = Duration(seconds: 10);
  static const Duration wsReconnectBaseDelay = Duration(milliseconds: 500);
  static const int wsMaxReconnectAttempts = 8;
  static const Duration wsPingInterval = Duration(seconds: 20);

  // ── UI ────────────────────────────────────────────────────────────────────
  static const Duration partialFadeDelay = Duration(milliseconds: 300);
  static const int maxDisplayedSegments = 6;

  // ── Colors ────────────────────────────────────────────────────────────────
  static const int primaryColorHex = 0xFF6C63FF;
  static const int backgroundColorHex = 0xFF0D0D14;
  static const int surfaceColorHex = 0xFF1A1A2E;
  static const int cardColorHex = 0xFF16213E;
}
