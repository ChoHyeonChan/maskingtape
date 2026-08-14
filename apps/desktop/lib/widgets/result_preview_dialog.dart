import 'dart:io';

import 'package:flutter/material.dart';

import '../models/detection.dart';
import '../models/file_task.dart';
import '../services/file_reader.dart';
import '../theme.dart';

/// 미리보기에 필요한 원문·마스킹 텍스트 한 쌍. 열 때 디스크에서 읽는다.
class _PreviewTexts {
  const _PreviewTexts({required this.original, required this.masked});

  final String original;
  final String masked;
}

/// 완료된 파일의 원문(탐지 하이라이트)과 마스킹 결과를 나란히 보여주는 다이얼로그.
///
/// 텍스트는 메모리에 들고 있지 않고 **열 때 디스크에서 읽는다**(대량 파일 안정화):
/// 원문은 원본 파일을 FileReader로 다시 읽고(탐지 offset과 같은 기준), 마스킹 결과는
/// 저장해 둔 `_masked` 파일을 읽는다.
class ResultPreviewDialog extends StatefulWidget {
  const ResultPreviewDialog({super.key, required this.task});

  final FileTask task;

  @override
  State<ResultPreviewDialog> createState() => _ResultPreviewDialogState();
}

class _ResultPreviewDialogState extends State<ResultPreviewDialog> {
  late final Future<_PreviewTexts> _texts = _load();

  Future<_PreviewTexts> _load() async {
    final task = widget.task;
    final outputPath = task.outputPath;
    if (outputPath == null) {
      throw const FileReadException('저장된 결과 파일 정보가 없습니다');
    }
    // 원문: 처리 때와 같은 FileReader로 읽어 탐지 offset이 어긋나지 않게 한다.
    final original = await const FileReader().read(task.path);
    final masked = await File(outputPath).readAsString();
    return _PreviewTexts(original: original, masked: masked);
  }

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
                      widget.task.name,
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
                '탐지 ${widget.task.detections.length}건 — '
                '${Detection.summarize(widget.task.detections)}',
                style: textTheme.bodyMedium
                    ?.copyWith(color: colors.onSurfaceVariant),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: FutureBuilder<_PreviewTexts>(
                  future: _texts,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState != ConnectionState.done) {
                      return const Center(child: CircularProgressIndicator());
                    }
                    if (snapshot.hasError) {
                      return _ErrorBody(error: snapshot.error!);
                    }
                    return _Comparison(
                      texts: snapshot.data!,
                      detections: widget.task.detections,
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 원문 파일이 삭제·변경돼 다시 못 읽을 때의 안내.
class _ErrorBody extends StatelessWidget {
  const _ErrorBody({required this.error});

  final Object error;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.error_outline, color: colors.error, size: 36),
          const SizedBox(height: 12),
          Text(
            '미리보기를 열 수 없습니다\n$error',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}

/// 원문(하이라이트) vs 마스킹 결과 좌우 비교.
class _Comparison extends StatelessWidget {
  const _Comparison({required this.texts, required this.detections});

  final _PreviewTexts texts;
  final List<Detection> detections;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colors = Theme.of(context).colorScheme;
    return Row(
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
            child: SelectableText(texts.masked, style: textTheme.bodyMedium),
          ),
        ),
      ],
    );
  }

  /// 원문을 탐지 구간 기준으로 잘라, 탐지된 부분에 페리윙클 하이라이트를 입힌다.
  List<TextSpan> _highlightedSpans(ColorScheme colors) {
    final text = texts.original;
    final ordered = [...detections]..sort((a, b) => a.start - b.start);
    final spans = <TextSpan>[];
    var cursor = 0;
    for (final d in ordered) {
      // 원본이 처리 후 바뀌었으면 offset이 범위를 벗어날 수 있다 — 안전하게 건너뛴다.
      if (d.start < cursor || d.end > text.length || d.start > d.end) {
        continue;
      }
      if (d.start > cursor) {
        spans.add(TextSpan(text: text.substring(cursor, d.start)));
      }
      spans.add(
        TextSpan(
          text: text.substring(d.start, d.end),
          // 탐지 구간은 "테이프가 붙을 자리"다 — 앱의 시그니처 색으로 표시한다.
          style: const TextStyle(
            backgroundColor: AppTheme.tapeSoft,
            color: AppTheme.tapeDeep,
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
