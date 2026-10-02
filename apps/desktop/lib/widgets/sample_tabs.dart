// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'package:flutter/material.dart';

import '../models/detection.dart';
import '../models/sample_texts.dart';
import '../theme.dart';

/// 스캔 전 「탐지 결과 조정」 자리를 채우는 샘플 문서 서랍 — 웹 `SampleTabs`와 같은 구성(#587).
///
/// 서류철 인덱스처럼 위쪽 탭(꼬리표)에 문서 유형을 달고, 탭을 고르면 그 샘플에 들어 있는
/// 개인정보 종류 태그와 원문을 미리 보여준다. 「입력창에 넣기」를 눌러야 실제 입력이
/// 바뀌어, 둘러보기만 해도 쓰던 글이 날아가지 않는다.
///
/// 웹은 탭을 한 줄에 두고 가로로 스크롤하지만, 데스크톱은 패널 폭이 고정돼 끝쪽 탭이 잘려
/// 보였다. 여기서는 탭이 폭에 맞춰 **여러 줄로 접힌다** — 9개가 전부 보인다. 창이 아주 작으면
/// 줄이 너무 늘어 미리보기 자리가 모자라므로 러너가 창 최소 크기(1024×680)를 둔다.
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
              // 자리만 잡는 보이지 않는 탭 줄 + 본문. 탭이 몇 줄로 접히든 본문은 그 아래에서
              // 시작한다(탭 줄 높이를 미리 알 수 없어 같은 내용을 한 번 더 깔아 재는 셈).
              Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Visibility(
                    visible: false,
                    maintainSize: true,
                    maintainState: true,
                    maintainAnimation: true,
                    child: _tabRows(selected: null),
                  ),
                  Expanded(child: _preview(context, active)),
                ],
              ),
              // 보이는 탭 줄은 본문 다음에 그려 본문 위 테두리를 덮는다. 보이는 줄은 자리 줄보다
              // 1px 길고 줄 간격은 1px 짧아, 마지막 줄의 바닥이 본문 위 테두리 위에 정확히 겹친다
              // — 선택한 탭은 본문 색으로 이어지고, 나머지 탭의 아래 변은 그 테두리와 포개진다.
              Positioned(
                top: 0,
                left: 0,
                right: 0,
                child: _tabRows(selected: _index),
              ),
            ],
          ),
        ),
      ],
    );
  }

  /// [selected]가 null이면 자리만 잡는 줄(전부 선택 안 된 높이, 보이지 않음).
  Widget _tabRows({required int? selected}) {
    final visible = selected != null;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Wrap(
        spacing: 4,
        runSpacing: visible ? _Tab.runSpacing - 1 : _Tab.runSpacing,
        crossAxisAlignment: WrapCrossAlignment.end,
        children: [
          for (var i = 0; i < widget.samples.length; i++)
            _Tab(
              label: widget.samples[i].label,
              selected: i == selected,
              visible: visible,
              onTap: () => setState(() => _index = i),
            ),
        ],
      ),
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
          // 종류 태그도 스크롤 안에 — 패널이 좁고 낮으면(태그가 서너 줄로 접힐 때) 태그만으로
          // 자리가 차서 넘친다. 웹은 태그를 고정해 두지만 폭이 넓어 그럴 일이 없다.
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Wrap(
                    spacing: 5,
                    runSpacing: 5,
                    children: [
                      for (final kind in sample.kinds)
                        _KindTag(Detection.labelOf(kind)),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    sample.text,
                    style: textTheme.bodyMedium?.copyWith(height: 1.65),
                  ),
                ],
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

/// 서류철 꼬리표 하나 — 웹 `.sample-tabs__tab`. 선택한 탭은 본문 색으로 위로 더 솟는다.
///
/// 높이 규칙(픽셀): 자리 줄은 34(위 여백 3 + 31). 보이는 줄은 35 — 선택 안 된 탭은 위 여백 4 + 31,
/// 선택한 탭은 36으로 그린 뒤 아래 1px(아래 변 테두리)을 잘라 35로 맞춘다. Flutter는 네 변
/// 색이 다른 둥근 테두리를 허용하지 않아 "아래 변만 본문 색"을 이렇게 흉내 낸다.
class _Tab extends StatelessWidget {
  const _Tab({
    required this.label,
    required this.selected,
    required this.visible,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final bool visible;
  final VoidCallback onTap;

  static const runSpacing = 4.0;
  static const _body = 31.0;
  static const _selectedBody = 36.0;

  @override
  Widget build(BuildContext context) {
    final tab = InkWell(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(10)),
      onTap: onTap,
      child: Container(
        height: selected ? _selectedBody : _body,
        padding: const EdgeInsets.symmetric(horizontal: 13),
        decoration: BoxDecoration(
          color: selected ? AppTheme.brandTint : AppTheme.brandSoft,
          border: Border.all(color: AppTheme.border),
          borderRadius: const BorderRadius.vertical(top: Radius.circular(10)),
        ),
        // Wrap 안에서는 폭이 bounded라 Container의 alignment를 쓰면 한 줄 전체로 늘어난다 —
        // widthFactor로 글자 폭만큼만 차지하게 하고 세로만 가운데 맞춘다.
        child: Center(
          widthFactor: 1,
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
    if (selected) {
      return ClipRect(
        child: Align(
          alignment: Alignment.topLeft,
          // widthFactor가 없으면 Wrap 안에서 한 줄 전체를 차지해 자리 줄과 다르게 접힌다.
          widthFactor: 1,
          heightFactor: (_selectedBody - 1) / _selectedBody,
          child: tab,
        ),
      );
    }
    return Padding(
      padding: EdgeInsets.only(top: visible ? 4 : 3),
      child: tab,
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
