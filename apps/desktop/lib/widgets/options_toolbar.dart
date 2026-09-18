import 'package:flutter/material.dart';

import '../services/anonymizer.dart';

/// 비식별화 옵션 조작부 — 이름 정밀 탐지 토글 + 전략 선택.
///
/// 파일 일괄 모드와 텍스트 입력 모드가 같은 옵션을 쓰므로 위젯을 하나로 둔다.
/// 옵션 값 자체는 부모(홈 화면)가 들고 있어 모드를 오가도 선택이 유지된다.
class OptionsToolbar extends StatelessWidget {
  const OptionsToolbar({
    super.key,
    required this.options,
    required this.onChanged,
    required this.enabled,
    this.onLlmTurnedOn,
  });

  final AnonymizeOptions options;
  final ValueChanged<AnonymizeOptions> onChanged;

  /// 처리 중에는 옵션을 바꾸지 못하게 잠근다.
  final bool enabled;

  /// 이름 정밀 탐지를 켜는 순간 호출 — 부모가 LLM 상태를 다시 확인하는 데 쓴다.
  final VoidCallback? onLlmTurnedOn;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 12,
      runSpacing: 8,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Tooltip(
          message:
              '이름을 규칙 대신 로컬 LLM으로 판단합니다.\n'
              '이 PC에서 Ollama가 실행 중이어야 합니다.',
          child: FilterChip(
            avatar: const Icon(Icons.psychology_outlined, size: 18),
            label: const Text('이름 정밀 탐지'),
            selected: options.useLlm,
            onSelected: !enabled
                ? null
                : (on) {
                    onChanged(options.copyWith(useLlm: on));
                    // 켜는 순간 상태를 새로 확인한다 — 그 사이 Ollama를 띄웠을 수
                    // 있고, 지금이 사용자가 가장 알고 싶은 시점이다.
                    if (on) onLlmTurnedOn?.call();
                  },
          ),
        ),
        SegmentedButton<MaskStrategy>(
          segments: [
            for (final s in MaskStrategy.values)
              ButtonSegment(value: s, label: Text(s.displayName)),
          ],
          selected: {options.strategy},
          onSelectionChanged: !enabled
              ? null
              : (selection) =>
                    onChanged(options.copyWith(strategy: selection.first)),
        ),
      ],
    );
  }
}
