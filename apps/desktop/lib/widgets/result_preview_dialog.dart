import 'package:flutter/material.dart';

import '../models/detection.dart';
import '../models/file_task.dart';
import '../theme.dart';

/// 완료된 파일의 원문(탐지 하이라이트)과 마스킹 결과를 나란히 보여주는 다이얼로그.
class ResultPreviewDialog extends StatelessWidget {
  const ResultPreviewDialog({super.key, required this.task});

  final FileTask task;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colors = Theme.of(context).colorScheme;

    return Dialog(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 1000, maxHeight: 640),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      task.name,
                      style: textTheme.titleLarge,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close),
                    tooltip: '닫기',
                  ),
                ],
              ),
              Text(
                '탐지 ${task.detections.length}건 — ${Detection.summarize(task.detections)}',
                style: textTheme.bodyMedium
                    ?.copyWith(color: colors.onSurfaceVariant),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      child: _Pane(
                        title: '원문',
                        child: SelectableText.rich(
                          TextSpan(
                            style: textTheme.bodyMedium,
                            children: _highlightedSpans(colors),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: _Pane(
                        title: '마스킹 결과',
                        child: SelectableText(
                          task.maskedText ?? '',
                          style: textTheme.bodyMedium,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 원문을 탐지 구간 기준으로 잘라, 탐지된 부분에 페리윙클 하이라이트를 입힌다.
  /// 밝은 배경 칩 + 진한 글자는 라이트/다크 어디서나 같은 색으로 읽힌다.
  List<TextSpan> _highlightedSpans(ColorScheme colors) {
    final text = task.originalText ?? '';
    final ordered = [...task.detections]..sort((a, b) => a.start - b.start);
    final spans = <TextSpan>[];
    var cursor = 0;
    for (final d in ordered) {
      if (d.start > cursor) {
        spans.add(TextSpan(text: text.substring(cursor, d.start)));
      }
      spans.add(
        TextSpan(
          text: text.substring(d.start, d.end),
          style: const TextStyle(
            backgroundColor: AppTheme.runBg,
            color: AppTheme.runFg,
            fontWeight: FontWeight.w700,
          ),
        ),
      );
      cursor = d.end;
    }
    if (cursor < text.length) {
      spans.add(TextSpan(text: text.substring(cursor)));
    }
    return spans;
  }
}

/// 제목 달린 테두리 패널 — 내용은 스크롤된다.
class _Pane extends StatelessWidget {
  const _Pane({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: 8),
        Expanded(
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              border: Border.all(color: colors.outlineVariant),
              borderRadius: BorderRadius.circular(8),
            ),
            child: SingleChildScrollView(
              child: Align(alignment: Alignment.topLeft, child: child),
            ),
          ),
        ),
      ],
    );
  }
}
