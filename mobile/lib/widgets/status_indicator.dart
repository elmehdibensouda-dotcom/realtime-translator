import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../models/translator_provider.dart';

/// Status pill showing current app state with appropriate color and icon.
class StatusIndicatorWidget extends StatelessWidget {
  final AppStatus status;
  const StatusIndicatorWidget({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    final (label, color, icon) = _config(status);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 400),
      curve: Curves.easeInOut,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (status == AppStatus.listening)
            _PulseIcon(color: color, icon: icon)
          else if (status == AppStatus.reconnecting)
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                color: color,
                strokeWidth: 2,
              ),
            )
          else
            Icon(icon, color: color, size: 16),
          const SizedBox(width: 8),
          Text(
            label,
            style: GoogleFonts.inter(
              color: color,
              fontSize: 13,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }

  (String, Color, IconData) _config(AppStatus status) {
    switch (status) {
      case AppStatus.idle:
        return ('Ready', const Color(0xFF8888AA), Icons.circle_outlined);
      case AppStatus.listening:
        return ('Listening', const Color(0xFF4ECCA3), Icons.mic);
      case AppStatus.processing:
        return ('Processing', const Color(0xFF6C63FF), Icons.autorenew);
      case AppStatus.reconnecting:
        return ('Reconnecting', const Color(0xFFFFCC00), Icons.wifi_off);
      case AppStatus.error:
        return ('Error', const Color(0xFFFF5252), Icons.error_outline);
    }
  }
}

class _PulseIcon extends StatefulWidget {
  final Color color;
  final IconData icon;
  const _PulseIcon({required this.color, required this.icon});

  @override
  State<_PulseIcon> createState() => _PulseIconState();
}

class _PulseIconState extends State<_PulseIcon>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _scale;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat(reverse: true);
    _scale = Tween<double>(begin: 0.85, end: 1.15).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ScaleTransition(
      scale: _scale,
      child: Icon(widget.icon, color: widget.color, size: 16),
    );
  }
}
