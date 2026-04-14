import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:logger/logger.dart';
import 'package:record/record.dart';
import 'package:permission_handler/permission_handler.dart';

import '../utils/constants.dart';

final _logger = Logger(printer: PrettyPrinter(methodCount: 0));

/// Captures microphone audio and emits PCM chunks via a broadcast stream.
///
/// Audio spec: 16 kHz, mono, 16-bit signed little-endian (PCM).
/// Each emitted chunk is [AppConstants.chunkMs] ms of audio.
class AudioCaptureService {
  final AudioRecorder _recorder = AudioRecorder();
  StreamSubscription<Uint8List>? _subscription;
  final _controller = StreamController<Uint8List>.broadcast();

  bool _isRecording = false;

  Stream<Uint8List> get audioStream => _controller.stream;
  bool get isRecording => _isRecording;

  /// Request microphone permission.
  Future<bool> requestPermission() async {
    final status = await Permission.microphone.request();
    return status.isGranted;
  }

  /// Start capturing and emitting audio chunks.
  Future<void> start() async {
    if (_isRecording) return;

    final hasPermission = await requestPermission();
    if (!hasPermission) {
      throw Exception('Microphone permission denied');
    }

    final config = RecordConfig(
      encoder: AudioEncoder.pcm16bits,
      sampleRate: AppConstants.sampleRate,
      numChannels: AppConstants.channels,
      bitRate: AppConstants.sampleRate * AppConstants.bitDepth * AppConstants.channels,
      autoGain: true,
      echoCancel: true,
      noiseSuppress: true,
    );

    final stream = await _recorder.startStream(config);
    _isRecording = true;
    _logger.i('Audio capture started (${AppConstants.sampleRate} Hz, ${AppConstants.chunkMs} ms chunks)');

    // Buffer incoming data into fixed-size chunks
    final bytesPerChunk = (AppConstants.sampleRate *
            AppConstants.channels *
            (AppConstants.bitDepth ~/ 8) *
            AppConstants.chunkMs) ~/
        1000;

    final buffer = BytesBuilder();

    _subscription = stream.listen(
      (data) {
        buffer.add(data);
        while (buffer.length >= bytesPerChunk) {
          final built = buffer.toBytes();
          _controller.add(Uint8List.fromList(built.sublist(0, bytesPerChunk)));
          buffer.clear();
          if (built.length > bytesPerChunk) {
            buffer.add(built.sublist(bytesPerChunk));
          }
        }
      },
      onError: (Object err) {
        _logger.e('Audio stream error: $err');
        _controller.addError(err);
      },
      onDone: () {
        _logger.i('Audio stream done');
      },
    );
  }

  Future<void> stop() async {
    if (!_isRecording) return;
    _isRecording = false;
    await _subscription?.cancel();
    _subscription = null;
    await _recorder.stop();
    _logger.i('Audio capture stopped');
  }

  Future<void> dispose() async {
    await stop();
    await _controller.close();
    _recorder.dispose();
  }
}
