// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

import '../models/detection.dart';
import '../models/sample_texts.dart';
import '../theme.dart';

/// 스캔 전 「탐지 결과 조정」 자리를 채우는 샘플 문서 서랍 — 웹 `SampleTabs`와 같은 구성(#587).
///
/// 서류철 인덱스처럼 위쪽 탭(꼬리표)에 문서 유형을 달고, 탭을 고르면 그 샘플에 들어 있는
/// 개인정보 종류 태그와 원문을 미리 보여준다. 「입력창에 넣기」를 눌러야 실제 입력이
/// 바뀌어, 둘러보기만 해도 쓰던 글이 날아가지 않는다.
class SampleTabs extends StatefulWidget {
  const SampleTabs({
    super.key,
    required this.onPick,
    this.samples = SampleText.all,
  });

  final ValueChanged<String> onPick;
  final List<SampleText> samples;

  @override
  State<SampleTabs> createState() => _SampleTabsState();
}

class _SampleTabsState extends State<SampleTabs> {
  int _index = 0;
  final _tabScroll = ScrollController();

  // 탭 줄의 높이. 선택한 탭은 1px 더 길게 그려 본문 위 테두리를 덮고(본문과 이어진 꼬리표),
  // 그 1px은 잘라낸다 — Flutter는 네 변 색이 다른 테두리에 둥근 모서리를 허용하지 않아서
  // "아래 변만 본문 색" 대신 이렇게 겹쳐 그린다.
  static const _rowHeight = 34.0;
  static const _selectedHeight = _rowHeight + 1;

  @override
  void dispose() {
    _tabScroll.dispose();
    super.dispose();
  }

  /// 탭 줄 위에서 세로 휠을 가로 스크롤로 — 탭이 패널 폭보다 많을 때 끝쪽 탭에 닿게(웹과 같다).
  void _onPointerSignal(PointerSignalEvent event) {
    if (event is! PointerScrollEvent || !_tabScroll.hasClients) return;
    final max = _tabScroll.position.maxScrollExtent;
    if (max <= 0) return;
    _tabScroll.jumpTo((_tabScroll.offset + event.scrollDelta.dy).clamp(0.0, max));
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final active = widget.samples[_index];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          '샘플 문서를 골라 입력창에 넣어보세요. 탐지를 실행하면 이 자리에 결과가 표시됩니다.',
          style: textTheme.bodySmall?.copyWith(
            color: AppTheme.textSecondary,
            fontWeight: FontWeight.w700,
            height: 1.5,
          ),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: Stack(
            children: [
              // 본문을 먼저, 탭 줄을 나중에 그려 선택한 탭이 본문 위 테두리를 덮는다.
              Positioned.fill(
                top: _rowHeight - 1,
                child: _preview(context, active),
              ),
              Positioned(
                top: 0,
                left: 0,
                right: 0,
                child: Listener(
                  onPointerSignal: _onPointerSignal,
                  child: ClipRect(
                    child: Align(
                      alignment: Alignment.topLeft,
                      heightFactor: _rowHeight / _selectedHeight,
                      child: SizedBox(
                        height: _selectedHeight,
                        child: SingleChildScrollView(
                          controller: _tabScroll,
                          scrollDirection: Axis.horizontal,
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              for (var i = 0; i < widget.samples.length; i++) ...[
                                if (i > 0) const SizedBox(width: 4),
                                _Tab(
                                  label: widget.samples[i].label,
                                  selected: i == _index,
                                  onTap: () => setState(() => _index = i),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  /// 종류 태그 + 원문 미리보기 + 「입력창에 넣기」 — 웹 `.sample-tabs__panel`.
  Widget _preview(BuildContext context, SampleText sample) {
    final textTheme = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
      decoration: BoxDecoration(
        color: AppTheme.brandTint,
        border: Border.all(color: AppTheme.border),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: 5,
            runSpacing: 5,
            children: [
              for (final kind in sample.kinds) _KindTag(Detection.labelOf(kind)),
            ],
          ),
          const SizedBox(height: 12),
          Expanded(
            child: SingleChildScrollView(
              child: Text(
                sample.text,
                style: textTheme.bodyMedium?.copyWith(height: 1.65),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerRight,
            child: FilledButton(
              onPressed: () => widget.onPick(sample.text),
              child: const Text('입력창에 넣기'),
            ),
          ),
        ],
      ),
    );
  }
}

/// 서류철 꼬리표 하나 — 웹 `.sample-tabs__tab`. 선택한 탭은 본문 색으로 위로 더 길다.
class _Tab extends StatelessWidget {
  const _Tab({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      // 선택 안 된 탭은 3px 낮게 — 바닥은 같고 선택한 탭만 위로 솟아 보인다.
      padding: EdgeInsets.only(top: selected ? 0 : 3),
      child: InkWell(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(10)),
        onTap: onTap,
        child: Container(
          height: selected
              ? _SampleTabsState._selectedHeight
              : _SampleTabsState._rowHeight - 3,
          padding: const EdgeInsets.symmetric(horizontal: 13),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: selected ? AppTheme.brandTint : AppTheme.brandSoft,
            border: Border.all(color: AppTheme.border),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(10)),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12.5,
              fontWeight: FontWeight.w800,
              color: selected ? AppTheme.brand : AppTheme.textSecondary,
            ),
          ),
        ),
      ),
    );
  }
}

/// 종류 태그 알약 — 웹 `.example-card__kind-tag`(흰 바탕, 옅은 테두리).
class _KindTag extends StatelessWidget {
  const _KindTag(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: AppTheme.surfaceStrong,
        border: Border.all(color: AppTheme.border),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: AppTheme.textSecondary,
        ),
      ),
    );
  }
}
