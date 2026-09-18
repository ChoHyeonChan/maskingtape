import 'package:flutter/material.dart';

import '../models/detection.dart';
import '../theme.dart';
import 'detection_list.dart';
import 'panel.dart';

/// 「탐지 결과 조정」 패널 — 건수 배지, 요약 줄, 순서대로/카테고리별 정렬, 항목별 가림 토글.
///
/// 웹 결과 패널과 같은 구성이되 **「일괄 조정」 확신도 다이얼은 넣지 않는다**(#401):
/// 확신도가 종류별 상수(계좌 0.6·운전면허 0.85·생년월일 0.9)라 임계값을 조금만 올려도
/// 그 종류가 통째로 노출된다. 무엇이 사라지는지 보이는 항목별 토글만 둔다.
///
/// 정렬 기준은 이 패널이 들고(보이는 순서일 뿐이라), 가림/노출 상태는 결과 텍스트를
/// 다시 만드는 부모가 든다.
class DetectionPanel extends StatefulWidget {
  const DetectionPanel({
    super.key,
    required this.detections,
    required this.isMasked,
    required this.onToggle,
    this.toggleEnabled = true,
    this.disabledNote,
  });

  /// null이면 아직 실행 전 — 안내 문구만 보인다.
  final List<Detection>? detections;
  final bool Function(Detection) isMasked;
  final void Function(Detection, bool masked) onToggle;

  /// false면 토글이 흐려진다(가명 전략). 이유는 [disabledNote]로 보여준다.
  final bool toggleEnabled;
  final String? disabledNote;

  @override
  State<DetectionPanel> createState() => _DetectionPanelState();
}

class _DetectionPanelState extends State<DetectionPanel> {
  bool _byKind = false;

  List<Detection> get _ordered {
    final list = [...widget.detections!];
    if (_byKind) {
      // 웹과 같은 기준 — 종류명 가나다순, 같은 종류 안에서는 원문 순서.
      list.sort((a, b) {
        final byLabel = a.kindLabel.compareTo(b.kindLabel);
        return byLabel != 0 ? byLabel : a.start - b.start;
      });
    } else {
      list.sort((a, b) => a.start - b.start);
    }
    return list;
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final detections = widget.detections;

    if (detections == null) {
      return Panel(
        title: '탐지 결과',
        child: Text(
          '왼쪽에 텍스트를 입력하고 개인정보 탐지 및 마스킹을 실행하면 '
          '결과가 여기에 표시됩니다.',
          style: textTheme.bodyMedium?.copyWith(color: colors.onSurfaceVariant),
        ),
      );
    }

    final maskedCount = detections.where(widget.isMasked).length;
    final exposedCount = detections.length - maskedCount;

    return Panel(
      title: '탐지 결과 조정',
      actions: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          decoration: BoxDecoration(
            color: AppTheme.brandSoft,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            '총 ${detections.length}건 발견',
            style: textTheme.titleSmall?.copyWith(color: AppTheme.action),
          ),
        ),
      ],
      child: detections.isEmpty
          ? Text(
              '개인정보가 탐지되지 않았습니다.',
              style: textTheme.bodyMedium?.copyWith(
                color: colors.onSurfaceVariant,
              ),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (widget.disabledNote != null) ...[
                  _Note(widget.disabledNote!),
                  const SizedBox(height: 10),
                ],
                Wrap(
                  alignment: WrapAlignment.spaceBetween,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  runSpacing: 8,
                  children: [
                    Text(
                      '개인정보 ${detections.length}건 발견 · '
                      '$maskedCount건 가림 · $exposedCount건 노출',
                      style: textTheme.bodySmall?.copyWith(
                        color: colors.onSurfaceVariant,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    _SortPill(
                      byKind: _byKind,
                      onChanged: (v) => setState(() => _byKind = v),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Expanded(
                  child: DetectionList(
                    detections: _ordered,
                    isMasked: widget.isMasked,
                    onToggle: widget.onToggle,
                    toggleEnabled: widget.toggleEnabled,
                  ),
                ),
              ],
            ),
    );
  }
}

/// 「순서대로 | 카테고리별」 알약 — 웹 `.detect__sort`와 같은 모양(선택 칸만 남색).
class _SortPill extends StatelessWidget {
  const _SortPill({required this.byKind, required this.onChanged});

  final bool byKind;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        color: AppTheme.brandTint,
        border: Border.all(color: AppTheme.borderSoft),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _SortChoice(
            label: '순서대로',
            active: !byKind,
            onTap: () => onChanged(false),
          ),
          _SortChoice(
            label: '카테고리별',
            active: byKind,
            onTap: () => onChanged(true),
          ),
        ],
      ),
    );
  }
}

class _SortChoice extends StatelessWidget {
  const _SortChoice({
    required this.label,
    required this.active,
    required this.onTap,
  });

  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
        decoration: BoxDecoration(
          color: active ? AppTheme.brand : Colors.transparent,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11.5,
            fontWeight: FontWeight.w800,
            color: active ? Colors.white : AppTheme.textSecondary,
          ),
        ),
      ),
    );
  }
}

/// 옅은 남색 안내 상자 — 가명 전략에서 항목별 조정이 왜 안 되는지.
class _Note extends StatelessWidget {
  const _Note(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      decoration: BoxDecoration(
        color: AppTheme.brandTint,
        border: Border.all(color: AppTheme.borderSoft),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        text,
        style: Theme.of(
          context,
        ).textTheme.bodySmall?.copyWith(color: AppTheme.textSecondary),
      ),
    );
  }
}
