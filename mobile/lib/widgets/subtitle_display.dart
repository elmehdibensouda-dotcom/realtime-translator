import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';

import '../models/transcript_model.dart';

/// Displays committed subtitle segments + current partial line.
class SubtitleDisplay extends StatefulWidget {
  final List<SubtitleSegment> segments;
  final String partialFr;
  final String partialEn;

  const SubtitleDisplay({
    super.key,
    required this.segments,
    required this.partialFr,
    required this.partialEn,
  });

  @override
  State<SubtitleDisplay> createState() => _SubtitleDisplayState();
}

class _SubtitleDisplayState extends State<SubtitleDisplay> {
  final _scrollController = ScrollController();

  @override
  void didUpdateWidget(SubtitleDisplay oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Auto-scroll to bottom when content changes
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A2E),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: ListView(
          controller: _scrollController,
          padding: const EdgeInsets.all(20),
          children: [
            // Empty state
            if (widget.segments.isEmpty && widget.partialFr.isEmpty)
              _EmptyState(),

            // Committed segments
            ...widget.segments.asMap().entries.map((entry) {
              final segment = entry.value;
              return _SegmentTile(segment: segment)
                  .animate()
                  .fadeIn(duration: 400.ms)
                  .slideY(begin: 0.1, end: 0, duration: 300.ms);
            }),

            // Partial (in-progress) line
            if (widget.partialFr.isNotEmpty)
              _PartialTile(
                frText: widget.partialFr,
                enText: widget.partialEn,
              ).animate().fadeIn(duration: 200.ms),

            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}

// ── Committed segment ─────────────────────────────────────────────────────────

class _SegmentTile extends StatelessWidget {
  final SubtitleSegment segment;
  const _SegmentTile({required this.segment});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // French (primary)
          Text(
            segment.textFr,
            style: GoogleFonts.inter(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w600,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 4),
          // English (secondary)
          Text(
            segment.textEn,
            style: GoogleFonts.inter(
              color: Colors.white38,
              fontSize: 13,
              fontStyle: FontStyle.italic,
              height: 1.3,
            ),
          ),
          const SizedBox(height: 6),
          Divider(color: Colors.white.withOpacity(0.06), thickness: 1),
        ],
      ),
    );
  }
}

// ── Partial line ──────────────────────────────────────────────────────────────

class _PartialTile extends StatelessWidget {
  final String frText;
  final String enText;
  const _PartialTile({required this.frText, required this.enText});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF6C63FF).withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF6C63FF).withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _PulsingDot(),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  frText,
                  style: GoogleFonts.inter(
                    color: Colors.white70,
                    fontSize: 17,
                    fontWeight: FontWeight.w500,
                    height: 1.4,
                  ),
                ),
              ),
            ],
          ),
          if (enText.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              enText,
              style: GoogleFonts.inter(
                color: Colors.white24,
                fontSize: 12,
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _PulsingDot extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 8,
      height: 8,
      decoration: const BoxDecoration(
        shape: BoxShape.circle,
        color: Color(0xFF6C63FF),
      ),
    ).animate(onPlay: (c) => c.repeat()).scaleXY(
          end: 1.6,
          duration: 700.ms,
          curve: Curves.easeInOut,
        ).then().scaleXY(end: 1.0, duration: 700.ms, curve: Curves.easeInOut);
  }
}

// ── Empty state ───────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 200,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.subtitles_outlined,
              color: Colors.white12,
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              'Subtitles will appear here',
              style: GoogleFonts.inter(
                color: Colors.white24,
                fontSize: 15,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Press Start and begin speaking',
              style: GoogleFonts.inter(
                color: Colors.white12,
                fontSize: 13,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
