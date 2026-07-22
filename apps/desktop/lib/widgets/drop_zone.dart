import 'package:desktop_drop/desktop_drop.dart';
import 'package:flutter/material.dart';

import '../theme.dart';

/// OS 파일 드래그&드롭을 받는 영역. 찾아보기 버튼도 함께 제공한다.
/// 받은 파일의 경로 목록을 콜백으로 넘기기만 하고, 목록 관리는 화면이 한다.
class DropZone extends StatefulWidget {
  const DropZone({super.key, required this.onFilesDropped, this.onBrowse});

  final ValueChanged<List<String>> onFilesDropped;

  /// "파일 찾아보기" 클릭 시 호출 — null이면 버튼을 숨긴다.
  final VoidCallback? onBrowse;

  @override
  State<DropZone> createState() => _DropZoneState();
}

class _DropZoneState extends State<DropZone> {
  bool _hovering = false;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;

    return DropTarget(
      onDragEntered: (_) => setState(() => _hovering = true),
      onDragExited: (_) => setState(() => _hovering = false),
      onDragDone: (details) {
        setState(() => _hovering = false);
        final paths = details.files.map((f) => f.path).toList();
        if (paths.isNotEmpty) {
          widget.onFilesDropped(paths);
        }
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        width: double.infinity,
        decoration: BoxDecoration(
          color: _hovering ? AppTheme.runBg : colors.surface,
          borderRadius: BorderRadius.circular(16),
        ),
        child: CustomPaint(
          foregroundPainter: _DashedBorderPainter(
            color: _hovering ? colors.primary : AppTheme.dashedLine,
          ),
          child: LayoutBuilder(
            builder: (context, constraints) => constraints.maxHeight < 220
                ? _compactContent(context)
                : _tallContent(context),
          ),
        ),
      ),
    );
  }

  Widget _tallContent(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.upload_file_outlined, size: 64, color: colors.primary),
        const SizedBox(height: 16),
        Text('파일을 여기로 끌어다 놓으세요', style: textTheme.titleLarge),
        const SizedBox(height: 8),
        Text(
          '여러 문서를 한 번에 비식별화합니다',
          style: textTheme.bodyMedium?.copyWith(color: colors.onSurfaceVariant),
        ),
        if (widget.onBrowse != null) ...[
          const SizedBox(height: 12),
          _browseButton(),
        ],
      ],
    );
  }

  Widget _compactContent(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.upload_file_outlined, size: 30, color: colors.primary),
        const SizedBox(width: 12),
        Flexible(
          child: Text(
            '파일을 여기로 끌어다 놓으세요',
            style: textTheme.titleMedium,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        if (widget.onBrowse != null) ...[
          const SizedBox(width: 12),
          _browseButton(),
        ],
      ],
    );
  }

  Widget _browseButton() => TextButton.icon(
        onPressed: widget.onBrowse,
        icon: const Icon(Icons.folder_open_outlined),
        label: const Text('또는 파일 찾아보기'),
      );
}

/// 둥근 사각형 점선 테두리 — "여기에 놓는 자리"라는 드롭존 관용 표현.
class _DashedBorderPainter extends CustomPainter {
  const _DashedBorderPainter({required this.color});

  final Color color;

  static const strokeWidth = 2.0;
  static const dash = 9.0;
  static const gap = 7.0;
  static const radius = 16.0;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final path = Path()
      ..addRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(
            strokeWidth / 2,
            strokeWidth / 2,
            size.width - strokeWidth,
            size.height - strokeWidth,
          ),
          Radius.circular(radius),
        ),
      );

    for (final metric in path.computeMetrics()) {
      var distance = 0.0;
      while (distance < metric.length) {
        canvas.drawPath(
          metric.extractPath(distance, distance + dash),
          paint,
        );
        distance += dash + gap;
      }
    }
  }

  @override
  bool shouldRepaint(_DashedBorderPainter oldDelegate) =>
      color != oldDelegate.color;
}
