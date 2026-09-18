import 'package:flutter/material.dart';

import '../kind_colors.dart';
import '../models/detection.dart';

/// 탐지 목록 — 한 줄에 종류 점·종류명·잡힌 값·확신도. 웹 결과 패널의 행과 같은 구성이다.
///
/// 탐지가 없으면 "탐지 없음" 안내만 보인다 — 개인정보 도구에서 "아무것도 안 잡힘"은
/// 오류가 아니라 정상 결과이므로 빈 화면으로 두지 않는다.
class DetectionList extends StatelessWidget {
  const DetectionList({super.key, required this.detections});

  final List<Detection> detections;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    if (detections.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Text(
          '개인정보가 탐지되지 않았습니다.',
          textAlign: TextAlign.center,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: colors.onSurfaceVariant),
        ),
      );
    }
    final ordered = [...detections]..sort((a, b) => a.start - b.start);
    return ListView.separated(
      itemCount: ordered.length,
      separatorBuilder: (_, _) => const SizedBox(height: 6),
      itemBuilder: (context, i) => _DetectionRow(detection: ordered[i]),
    );
  }
}

class _DetectionRow extends StatelessWidget {
  const _DetectionRow({required this.detection});

  final Detection detection;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final kindColor = KindColors.of(detection.kind);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      decoration: BoxDecoration(
        color: colors.surface,
        border: Border.all(color: colors.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Container(
            width: 9,
            height: 9,
            decoration: BoxDecoration(color: kindColor, shape: BoxShape.circle),
          ),
          const SizedBox(width: 10),
          SizedBox(
            width: 96,
            child: Text(
              detection.kindLabel,
              style: textTheme.titleSmall,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          Expanded(
            child: Text(
              detection.text,
              style: textTheme.bodySmall?.copyWith(
                color: colors.onSurfaceVariant,
              ),
              overflow: TextOverflow.ellipsis,
              maxLines: 1,
            ),
          ),
          const SizedBox(width: 10),
          Text(
            '${(detection.confidence * 100).round()}%',
            style: textTheme.bodySmall?.copyWith(
              color: colors.onSurfaceVariant,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
