import 'package:flutter/material.dart';

import '../services/llm_status.dart';
import '../theme.dart';

/// 로컬 LLM 준비 상태를 보여주는 칩. 누르면 다시 확인한다.
///
/// 이름 정밀 탐지를 켜기 *전에* 상태가 보여야 의미가 있다 — Ollama를 켜야 하는지,
/// 모델을 받아야 하는지를 파일 처리에 실패한 뒤에 알게 되면 늦다.
class LlmStatusPill extends StatelessWidget {
  const LlmStatusPill({super.key, required this.status, required this.onRefresh});

  final LlmStatus status;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final isLight = Theme.of(context).brightness == Brightness.light;

    final (IconData icon, Color bg, Color fg) = switch (status.readiness) {
      LlmReadiness.checking => (Icons.more_horiz, AppTheme.waitBg, AppTheme.waitFg),
      LlmReadiness.offline => (Icons.cloud_off, AppTheme.failBg, AppTheme.failFg),
      LlmReadiness.modelMissing =>
        (Icons.download_outlined, AppTheme.failBg, AppTheme.failFg),
      LlmReadiness.downloaded => (Icons.schedule, AppTheme.waitBg, AppTheme.waitFg),
      LlmReadiness.loaded => (Icons.bolt, AppTheme.doneBg, AppTheme.doneFg),
    };

    final foreground = isLight ? fg : Color.lerp(fg, Colors.white, 0.35)!;

    return Tooltip(
      message: status.detail.isEmpty
          ? '눌러서 다시 확인'
          : '${status.detail}\n눌러서 다시 확인',
      child: InkWell(
        onTap: onRefresh,
        borderRadius: BorderRadius.circular(99),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          decoration: BoxDecoration(
            color: isLight ? bg : fg.withValues(alpha: 0.18),
            borderRadius: BorderRadius.circular(99),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 14, color: foreground),
              const SizedBox(width: 6),
              Text(
                status.label,
                style: TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w700,
                  color: foreground,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
