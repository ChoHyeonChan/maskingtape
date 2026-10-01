// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'package:flutter/material.dart';

import '../models/detection.dart';
import '../theme.dart';
import 'detection_list.dart';
import 'panel.dart';
import 'sample_tabs.dart';

/// 「탐지 결과 조정」 패널 — 건수 배지, 요약 줄, 순서대로/카테고리별 정렬, 항목별 가림 토글.
/// 스캔 전에는 같은 자리가 「샘플 선택하기」 서랍([SampleTabs])이다 — 웹과 같다(#587).
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
    this.onSamplePick,
  });

  /// null이면 아직 실행 전 — 안내 문구만 보인다.
  final List<Detection>? detections;
  final bool Function(Detection) isMasked;
  final void Function(Detection, bool masked) onToggle;

  /// false면 토글이 흐려진다(가명 전략). 이유는 [disabledNote]로 보여준다.
  final bool toggleEnabled;
  final String? disabledNote;

  /// 스캔 전 샘플 서랍에서 「입력창에 넣기」를 눌렀을 때 — 입력창을 채우는 건 부모의 일이다.
  final ValueChanged<String>? onSamplePick;

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
      // 스캔 전엔 이 자리가 샘플 서랍이라 제목도 그 역할에 맞춘다(웹과 같다).
      return Panel(
        title: '샘플 선택하기',
        child: SampleTabs(onPick: widget.onSamplePick ?? (_) {}),
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
                Expanded(
                  child: _Folder(
                    label: '수동 조정',
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
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
                  ),
                ),
              ],
            ),
    );
  }
}

/// 서류철 꼬리표가 달린 종이 영역 — 웹 `.detect-folder--manual`과 같은 모양(청록 꼬리표·옅은 청록 종이).
///
/// 웹은 「신뢰도 기준」(일괄 조정)·「수동 조정」 두 폴더를 두지만, 데스크톱은 일괄 조정을
/// 두지 않기로 했으므로(#401) 「수동 조정」 하나만 있다. 꼬리표는 본문보다 1px 아래까지
/// 그려 본문 위 테두리를 덮고 그 1px을 잘라낸다 — 네 변 색이 다른 둥근 테두리를 Flutter가
/// 허용하지 않아서다([SampleTabs]의 탭과 같은 수법).
class _Folder extends StatelessWidget {
  const _Folder({required this.label, required this.child});

  final String label;
  final Widget child;

  /// 웹 `--brand-cyan` / `--folder-paper`(수동 조정) 값.
  static const _accent = Color(0xFF167F9F);
  static const _paper = Color(0xFFF5FAFB);
  static const _labelHeight = 28.0;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned.fill(
          top: _labelHeight - 1,
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: _paper,
              border: Border.all(color: AppTheme.borderSoft),
              borderRadius: const BorderRadius.only(
                topRight: Radius.circular(12),
                bottomLeft: Radius.circular(12),
                bottomRight: Radius.circular(12),
              ),
            ),
            child: child,
          ),
        ),
        Positioned(
          top: 0,
          left: 0,
          child: ClipRect(
            child: Align(
              alignment: Alignment.topLeft,
              heightFactor: _labelHeight / (_labelHeight + 1),
              child: Container(
                height: _labelHeight + 1,
                padding: const EdgeInsets.fromLTRB(13, 0, 20, 0),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: _paper,
                  border: Border.all(color: AppTheme.borderSoft),
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(10),
                    topRight: Radius.circular(16),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 5.5,
                      height: 12,
                      decoration: BoxDecoration(
                        color: _accent,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                    const SizedBox(width: 7),
                    Text(
                      label,
                      style: const TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w800,
                        color: _accent,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
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
