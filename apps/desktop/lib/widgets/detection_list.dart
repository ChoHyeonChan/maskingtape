import 'package:flutter/material.dart';

import '../kind_colors.dart';
import '../models/detection.dart';
import 'mask_toggle.dart';

/// 탐지 목록 — 한 줄에 종류 점·종류명·잡힌 값·확신도·「가림」 토글. 웹 결과 패널의 행과 같다.
///
/// 항목의 가림/노출 상태는 부모가 들고 [isMasked]/[onToggle]로 내려준다 — 결과 텍스트를
/// 다시 만드는 쪽이 같은 상태를 봐야 하기 때문이다. [toggleEnabled]가 false면(가명 전략)
/// 토글이 흐려지고 눌리지 않는다.
class DetectionList extends StatelessWidget {
  const DetectionList({
    super.key,
    required this.detections,
    required this.isMasked,
    required this.onToggle,
    this.toggleEnabled = true,
  });

  /// 이미 정렬된 목록 — 정렬 기준은 부모(패널)가 정한다.
  final List<Detection> detections;
  final bool Function(Detection) isMasked;
  final void Function(Detection, bool masked) onToggle;
  final bool toggleEnabled;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      itemCount: detections.length,
      separatorBuilder: (_, _) => const SizedBox(height: 6),
      itemBuilder: (context, i) => _DetectionRow(
        detection: detections[i],
        masked: isMasked(detections[i]),
        enabled: toggleEnabled,
        onToggle: (m) => onToggle(detections[i], m),
      ),
    );
  }
}

class _DetectionRow extends StatelessWidget {
  const _DetectionRow({
    required this.detection,
    required this.masked,
    required this.enabled,
    required this.onToggle,
  });

  final Detection detection;
  final bool masked;
  final bool enabled;
  final ValueChanged<bool> onToggle;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final kindColor = KindColors.of(detection.kind);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
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
            width: 92,
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
                // 노출로 바꾼 항목은 값이 결과에 그대로 남는다 — 줄을 그어 눈에 띄게 한다.
                decoration: masked ? null : TextDecoration.underline,
                decorationStyle: TextDecorationStyle.dotted,
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
          const SizedBox(width: 10),
          MaskToggle(masked: masked, enabled: enabled, onChanged: onToggle),
        ],
      ),
    );
  }
}
