import 'package:flutter/material.dart';

import 'tape_strip.dart';

/// 테이프로 가려진 글자 — 빈 화면의 예시 문서에서 쓴다.
///
/// 아래 글자를 아주 옅게 남기는 이유: 완전히 지우면 그냥 색 막대지만, 윤곽이 어렴풋이
/// 남으면 "여기 뭔가 있었고 그걸 덮었다"로 읽힌다. 이 앱이 하는 일이 그것이다.
/// 값 자체는 읽을 수 없으므로 비식별화의 의미는 그대로다.
class RedactedText extends StatelessWidget {
  const RedactedText(this.text, {super.key});

  /// 가려질 글자 — **합성 값만** 넣는다. 이 위젯은 예시용이다.
  final String text;

  @override
  Widget build(BuildContext context) {
    return Stack(
      alignment: Alignment.center,
      children: [
        Padding(
          // 테이프가 좌우로 넘치는 만큼 자리를 미리 벌려둔다.
          padding: const EdgeInsets.symmetric(horizontal: 7),
          child: Opacity(
            // 테이프 아래로 윤곽만 비칠 정도. 이 값을 올리면 가려진 글자가 읽히는데,
            // 개인정보 도구의 대표 화면에서 그건 마스킹이 새는 것으로 보인다.
            opacity: 0.32,
            child: Text(text, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ),
        const Positioned.fill(
          // 글자보다 사방으로 넉넉히 덮는다 — 손으로 붙이면 딱 맞게 붙지 않고,
          // 무엇보다 기울어진 테이프의 모서리로 글자가 새면 안 된다.
          top: -3,
          bottom: -3,
          child: TapeStrip(height: null),
        ),
      ],
    );
  }
}
