import 'package:flutter/material.dart';

import '../models/file_task.dart';
import '../theme.dart';

/// 파일 상태를 한눈에 보여주는 파스텔 칩.
class StatusPill extends StatelessWidget {
  const StatusPill({super.key, required this.status});

  final FileTaskStatus status;

  @override
  Widget build(BuildContext context) {
    final isLight = Theme.of(context).brightness == Brightness.light;

    final (String label, Color bg, Color fg) = switch (status) {
      FileTaskStatus.waiting => ('대기', AppTheme.waitBg, AppTheme.waitFg),
      FileTaskStatus.processing => ('처리 중', AppTheme.runBg, AppTheme.runFg),
      FileTaskStatus.done => ('완료', AppTheme.doneBg, AppTheme.doneFg),
      FileTaskStatus.failed => ('실패', AppTheme.failBg, AppTheme.failFg),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      decoration: BoxDecoration(
        // 다크 모드에선 파스텔 배경 대신 글자색의 반투명 배경으로 대비를 지킨다.
        color: isLight ? bg : fg.withValues(alpha: 0.18),
        borderRadius: BorderRadius.circular(99),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11.5,
          fontWeight: FontWeight.w700,
          color: isLight ? fg : Color.lerp(fg, Colors.white, 0.35),
        ),
      ),
    );
  }
}
