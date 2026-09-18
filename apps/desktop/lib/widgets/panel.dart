import 'package:flutter/material.dart';

import '../theme.dart';

/// 제목·조작부가 달린 흰 패널 — 웹 `.panel`과 같은 테두리(남색 18%, 1.5px)·모서리(14).
///
/// 텍스트 입력 모드의 세 패널이 같은 틀을 쓴다. 제목 왼쪽 아이콘은 웹처럼 행동 파랑이다.
class Panel extends StatelessWidget {
  const Panel({
    super.key,
    required this.title,
    required this.child,
    this.icon,
    this.actions = const [],
  });

  final String title;
  final IconData? icon;
  final List<Widget> actions;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Material(
      color: colors.surface,
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppTheme.panelRadius),
        side: BorderSide(color: colors.outlineVariant, width: 1.5),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Wrap(
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              runSpacing: 8,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (icon != null) ...[
                      Icon(icon, size: 20, color: AppTheme.action),
                      const SizedBox(width: 8),
                    ],
                    Text(title, style: Theme.of(context).textTheme.titleLarge),
                  ],
                ),
                Wrap(spacing: 8, runSpacing: 6, children: actions),
              ],
            ),
            const SizedBox(height: 14),
            Expanded(child: child),
          ],
        ),
      ),
    );
  }
}

/// 얇은 테두리 안에 위에서부터 채워지며 스크롤되는 내용 — 결과 본문용.
class BorderedScroll extends StatelessWidget {
  const BorderedScroll({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        border: Border.all(color: colors.outlineVariant),
        borderRadius: BorderRadius.circular(AppTheme.controlRadius),
      ),
      child: SingleChildScrollView(
        child: Align(alignment: Alignment.topLeft, child: child),
      ),
    );
  }
}
