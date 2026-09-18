import 'package:flutter/material.dart';

import '../theme.dart';

/// 항목별 「가림 / 보임」 알약 토글 — 웹 `.detect-row__toggle`과 같은 모양.
///
/// 켜짐(가림)은 남색 바탕에 흰 글자, 꺼짐(보임)은 옅은 회색 바탕. 흰 손잡이가 반대편으로
/// 움직인다. 글자를 안에 두는 이유: 스위치만 있으면 "켜짐이 가림인지 보임인지"가
/// 헷갈리는데, 이 앱에서 그 혼동은 곧 노출 사고다.
class MaskToggle extends StatelessWidget {
  const MaskToggle({
    super.key,
    required this.masked,
    required this.onChanged,
    this.enabled = true,
  });

  final bool masked;
  final ValueChanged<bool> onChanged;
  final bool enabled;

  static const _width = 68.0;
  static const _height = 28.0;
  static const _knob = 20.0;

  @override
  Widget build(BuildContext context) {
    final label = masked ? '가림' : '보임';
    return Semantics(
      toggled: masked,
      label: masked ? '가려짐 — 눌러서 보이게 하기' : '보임 — 눌러서 가리기',
      child: Opacity(
        opacity: enabled ? 1 : 0.45,
        child: GestureDetector(
          onTap: enabled ? () => onChanged(!masked) : null,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            width: _width,
            height: _height,
            decoration: BoxDecoration(
              color: masked ? AppTheme.brand : const Color(0xFFEEF1F6),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                color: masked ? AppTheme.brand : AppTheme.borderSoft,
              ),
            ),
            child: Stack(
              alignment: Alignment.center,
              children: [
                AnimatedAlign(
                  duration: const Duration(milliseconds: 160),
                  alignment: masked
                      ? Alignment.centerLeft
                      : Alignment.centerRight,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 9),
                    child: Text(
                      label,
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        color: masked ? Colors.white : AppTheme.textSecondary,
                      ),
                    ),
                  ),
                ),
                AnimatedAlign(
                  duration: const Duration(milliseconds: 160),
                  alignment: masked
                      ? Alignment.centerRight
                      : Alignment.centerLeft,
                  child: Container(
                    width: _knob,
                    height: _knob,
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    decoration: const BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: Color(0x33102A68),
                          blurRadius: 3,
                          offset: Offset(0, 1),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
