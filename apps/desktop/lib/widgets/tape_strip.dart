import 'package:flutter/material.dart';

import '../theme.dart';

/// 이 앱의 시그니처 요소 — 손으로 뜯어 붙인 마스킹테이프 한 조각.
///
/// 왜 굳이 직접 그리는가: 개인정보를 가린다는 동작을 화면에서 **보여주는** 물건이
/// 필요해서다. 사각형 하이라이트는 어느 앱에나 있지만, 뜯긴 가장자리와 살짝 기울어진
/// 각도는 "테이프를 붙였다"로 읽힌다. 이름이 마스킹테이프인 도구가 화면에서 그걸
/// 보여주지 않으면 이름이 붕 뜬다.
///
/// 실제 마스킹테이프처럼 **살짝 비친다**(완전 불투명이 아니다) — 아래 글자의 윤곽이
/// 어렴풋이 남아 "여기에 뭔가 있었다"는 사실 자체는 보인다. 가려진 값이 무엇인지는
/// 알 수 없으므로 비식별화 의미는 그대로다.
class TapeStrip extends StatelessWidget {
  const TapeStrip({
    super.key,
    this.width,
    this.height = 22,
    this.rotation = -0.026,
    this.child,
  });

  /// null이면 부모가 주는 크기를 채운다(예: Positioned.fill로 글자 위에 덮을 때).
  final double? width;
  final double? height;

  /// 라디안. 0이면 반듯하게 붙은 테이프 — 기본값은 손으로 붙인 정도의 기울기다.
  final double rotation;

  /// 테이프 위에 얹을 것(예: 라벨). 보통은 비운다.
  final Widget? child;

  @override
  Widget build(BuildContext context) {
    return Transform.rotate(
      angle: rotation,
      child: CustomPaint(
        painter: const _TapePainter(),
        child: SizedBox(
          width: width,
          height: height,
          child: child == null
              ? null
              : Center(
                  child: DefaultTextStyle.merge(
                    style: const TextStyle(
                      color: AppTheme.tapeDeep,
                      fontWeight: FontWeight.w700,
                      fontSize: 11,
                      letterSpacing: 0.6,
                    ),
                    child: child!,
                  ),
                ),
        ),
      ),
    );
  }
}

/// 테이프 면 + 뜯긴 좌우 가장자리.
class _TapePainter extends CustomPainter {
  const _TapePainter();

  /// 뜯긴 가장자리의 들쭉날쭉함(픽셀). 프레임마다 흔들리면 안 되므로 고정값을 쓴다 —
  /// 난수를 쓰면 리빌드마다 모양이 바뀌어 눈에 거슬린다.
  /// 진폭이 2px대면 실제 화면(글자 높이 ~20px)에서 눈에 안 보여 그냥 노란 막대가 된다.
  /// 톱니를 크고 성기게 잡아야 "손으로 뜯었다"로 읽힌다.
  static const _tearLeft = <double>[0.5, 4.2, 1.2, 5.0, 2.0];
  static const _tearRight = <double>[4.0, 0.8, 4.8, 1.5, 3.4];

  @override
  void paint(Canvas canvas, Size size) {
    final path = Path()..moveTo(_tearLeft.first, 0);

    // 위쪽 가장자리 — 반듯하게 자른 면.
    path.lineTo(size.width - _tearRight.first, 0);

    // 오른쪽 — 뜯긴 면.
    for (var i = 1; i < _tearRight.length; i++) {
      path.lineTo(
        size.width - _tearRight[i],
        size.height * i / (_tearRight.length - 1),
      );
    }

    // 아래쪽 가장자리.
    path.lineTo(_tearLeft.last, size.height);

    // 왼쪽 — 뜯긴 면(아래에서 위로).
    for (var i = _tearLeft.length - 2; i >= 0; i--) {
      path.lineTo(_tearLeft[i], size.height * i / (_tearLeft.length - 1));
    }
    path.close();

    // 테이프 면 — 살짝 비친다.
    canvas.drawPath(
      path,
      Paint()..color = AppTheme.tape.withValues(alpha: 0.94),
    );

    // 붙은 테두리의 그늘 — 종이에서 살짝 떠 있는 느낌을 만든다.
    canvas.drawPath(
      path,
      Paint()
        ..color = AppTheme.tapeDeep.withValues(alpha: 0.22)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1,
    );

    // 종이 결 — 가로로 아주 옅은 선 두 줄. 매끈한 사각형이 아니라 재질로 보이게 한다.
    final grain = Paint()
      ..color = Colors.white.withValues(alpha: 0.30)
      ..strokeWidth = 1;
    canvas.drawLine(
      Offset(2, size.height * 0.32),
      Offset(size.width - 2, size.height * 0.32),
      grain,
    );
    canvas.drawLine(
      Offset(2, size.height * 0.68),
      Offset(size.width - 2, size.height * 0.68),
      grain,
    );
  }

  @override
  bool shouldRepaint(_TapePainter oldDelegate) => false;
}
