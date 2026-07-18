import 'package:flutter/material.dart';

/// 홈 화면 — 파일 드롭존 자리만 잡아둔 빈 화면.
/// 실제 드래그&드롭 수신은 다음 단계에서 붙인다 (라이선스 확인 + SBOM 절차 필요).
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('마스킹테이프 — 문서 일괄 비식별화'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(32),
        child: _DropZonePlaceholder(colors: colors),
      ),
    );
  }
}

/// 드롭존 자리 표시 위젯 — 안내 문구와 테두리만 있는 상태.
class _DropZonePlaceholder extends StatelessWidget {
  const _DropZonePlaceholder({required this.colors});

  final ColorScheme colors;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: colors.surfaceContainerLow,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colors.outlineVariant, width: 2),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.upload_file_outlined, size: 72, color: colors.primary),
          const SizedBox(height: 16),
          Text(
            '파일을 여기로 끌어다 놓으세요',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            '여러 문서를 한 번에 비식별화합니다',
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: colors.onSurfaceVariant),
          ),
        ],
      ),
    );
  }
}
