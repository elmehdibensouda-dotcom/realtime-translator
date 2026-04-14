import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Animated waveform visualiser – draws bars that animate with mic activity.
/// In production, feed real RMS values from the audio stream.
class WaveformWidget extends StatefulWidget {
  final int barCount;
  final Color color;

  const WaveformWidget({
    super.key,
    this.barCount = 32,
    this.color = const Color(0xFF6C63FF),
  });

  @override
  State<WaveformWidget> createState() => _WaveformWidgetState();
}

class _WaveformWidgetState extends State<WaveformWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  final _rng = math.Random();
  late List<double> _heights;

  @override
  void initState() {
    super.initState();
    _heights = List.generate(widget.barCount, (_) => 0.2);
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 80),
    )..addListener(_updateHeights)
      ..repeat();
  }

  void _updateHeights() {
    setState(() {
      for (int i = 0; i < widget.barCount; i++) {
        // Simulate audio amplitude – replace with real RMS in production
        _heights[i] = 0.1 + _rng.nextDouble() * 0.9;
      }
    });
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 80,
      child: CustomPaint(
        painter: _WaveformPainter(
          heights: _heights,
          color: widget.color,
        ),
        size: Size.infinite,
      ),
    );
  }
}

class _WaveformPainter extends CustomPainter {
  final List<double> heights;
  final Color color;

  _WaveformPainter({required this.heights, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final barWidth = size.width / (heights.length * 1.8);
    final spacing = barWidth * 0.8;
    final maxHeight = size.height * 0.9;

    for (int i = 0; i < heights.length; i++) {
      final barHeight = maxHeight * heights[i];
      final x = i * (barWidth + spacing) + spacing / 2;
      final y = (size.height - barHeight) / 2;

      final gradient = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          color.withOpacity(0.9),
          color.withOpacity(0.2),
        ],
      );

      final rect = RRect.fromRectAndRadius(
        Rect.fromLTWH(x, y, barWidth, barHeight),
        const Radius.circular(4),
      );

      canvas.drawRRect(
        rect,
        Paint()
          ..shader = gradient.createShader(rect.outerRect)
          ..style = PaintingStyle.fill,
      );
    }
  }

  @override
  bool shouldRepaint(_WaveformPainter old) => true;
}
