import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import '../models/translator_provider.dart';
import '../widgets/status_indicator.dart';
import '../widgets/subtitle_display.dart';
import '../widgets/waveform_widget.dart';
import '../utils/constants.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(translatorProvider);
    final notifier = ref.read(translatorProvider.notifier);
    final isListening = state.status == AppStatus.listening ||
        state.status == AppStatus.processing;

    return Scaffold(
      backgroundColor: const Color(AppConstants.backgroundColorHex),
      body: SafeArea(
        child: Column(
          children: [
            _AppBar(latencyMs: state.lastLatencyMs),
            const SizedBox(height: 8),
            StatusIndicatorWidget(status: state.status),
            const SizedBox(height: 12),
            // Waveform
            AnimatedContainer(
              duration: const Duration(milliseconds: 400),
              curve: Curves.easeInOut,
              height: isListening ? 80 : 0,
              child: isListening
                  ? const WaveformWidget().animate().fadeIn(duration: 300.ms)
                  : const SizedBox.shrink(),
            ),
            // Subtitles — fill remaining space
            Expanded(
              child: SubtitleDisplay(
                segments: state.segments,
                partialFr: state.partialFr,
                partialEn: state.partialEn,
              ),
            ),
            // Control button
            _ControlButton(
              isListening: isListening,
              onStart: notifier.startListening,
              onStop: notifier.stopListening,
              status: state.status,
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }
}

// ── App Bar ───────────────────────────────────────────────────────────────────

class _AppBar extends StatelessWidget {
  final double? latencyMs;
  const _AppBar({this.latencyMs});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Row(
        children: [
          // Logo + title
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF6C63FF), Color(0xFF3D8BFF)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.translate, color: Colors.white, size: 20),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Live Translator',
                style: GoogleFonts.inter(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text(
                'EN → FR  •  Real-time',
                style: GoogleFonts.inter(
                  color: Colors.white38,
                  fontSize: 11,
                ),
              ),
            ],
          ),
          const Spacer(),
          // Latency badge
          if (latencyMs != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: _latencyColor(latencyMs!).withOpacity(0.15),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: _latencyColor(latencyMs!).withOpacity(0.4),
                ),
              ),
              child: Text(
                '${latencyMs!.toStringAsFixed(0)} ms',
                style: GoogleFonts.inter(
                  color: _latencyColor(latencyMs!),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ).animate().fadeIn(),
        ],
      ),
    );
  }

  Color _latencyColor(double ms) {
    if (ms < 500) return const Color(0xFF4ECCA3);
    if (ms < 800) return const Color(0xFFFFCC00);
    return const Color(0xFFFF5252);
  }
}

// ── Control Button ────────────────────────────────────────────────────────────

class _ControlButton extends StatelessWidget {
  final bool isListening;
  final Future<void> Function() onStart;
  final Future<void> Function() onStop;
  final AppStatus status;

  const _ControlButton({
    required this.isListening,
    required this.onStart,
    required this.onStop,
    required this.status,
  });

  @override
  Widget build(BuildContext context) {
    final isReconnecting = status == AppStatus.reconnecting;
    final isError = status == AppStatus.error;

    return GestureDetector(
      onTap: isReconnecting ? null : (isListening ? onStop : onStart),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 350),
        curve: Curves.easeInOutCubic,
        width: isListening ? 80 : 140,
        height: 80,
        decoration: BoxDecoration(
          gradient: isError
              ? const LinearGradient(
                  colors: [Color(0xFFFF5252), Color(0xFFFF1744)],
                )
              : isListening
                  ? const LinearGradient(
                      colors: [Color(0xFFFF5252), Color(0xFFFF1744)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    )
                  : const LinearGradient(
                      colors: [Color(0xFF6C63FF), Color(0xFF3D8BFF)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
          borderRadius: BorderRadius.circular(isListening ? 40 : 24),
          boxShadow: [
            BoxShadow(
              color: (isListening
                      ? const Color(0xFFFF5252)
                      : const Color(0xFF6C63FF))
                  .withOpacity(0.4),
              blurRadius: 20,
              spreadRadius: 2,
            ),
          ],
        ),
        child: isReconnecting
            ? const Center(
                child: SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2.5,
                  ),
                ),
              )
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    isListening ? Icons.stop_rounded : Icons.mic_rounded,
                    color: Colors.white,
                    size: 28,
                  ),
                  if (!isListening) ...[
                    const SizedBox(width: 8),
                    Text(
                      'Start',
                      style: GoogleFonts.inter(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ],
              ),
      ),
    )
        .animate(target: isListening ? 1 : 0)
        .custom(
          duration: 1200.ms,
          curve: Curves.easeInOut,
          builder: (context, value, child) => child,
        );
  }
}
