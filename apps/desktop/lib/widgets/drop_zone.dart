import 'package:desktop_drop/desktop_drop.dart';
import 'package:flutter/material.dart';

import '../theme.dart';
import 'redacted_text.dart';

/// OS 파일 드래그&드롭을 받는 영역. 찾아보기 버튼도 함께 제공한다.
/// 받은 파일의 경로 목록을 콜백으로 넘기기만 하고, 목록 관리는 화면이 한다.
///
/// 빈 화면에서는 **예시 문서에 테이프가 붙은 모습**을 먼저 보여준다. 이 앱이 무엇을
/// 하는 도구인지 한 장면으로 말하는 자리라, 안내 문구보다 앞에 둔다.
///
/// 드롭 대상은 이 위젯 전체지만 점선 테두리는 **내용만 감싼다**. 예전처럼 점선이 창을
/// 가득 채우면 커다란 빈 상자로 보여서, 여백이 의도가 아니라 미완성으로 읽혔다.
class DropZone extends StatefulWidget {
  const DropZone({super.key, required this.onFilesDropped, this.onBrowse});

  final ValueChanged<List<String>> onFilesDropped;

  /// "파일 찾아보기" 클릭 시 호출 — null이면 버튼을 숨긴다.
  final VoidCallback? onBrowse;

  @override
  State<DropZone> createState() => _DropZoneState();
}

class _DropZoneState extends State<DropZone> {
  bool _hovering = false;

  @override
  Widget build(BuildContext context) {
    return DropTarget(
      onDragEntered: (_) => setState(() => _hovering = true),
      onDragExited: (_) => setState(() => _hovering = false),
      onDragDone: (details) {
        setState(() => _hovering = false);
        final paths = details.files.map((f) => f.path).toList();
        if (paths.isNotEmpty) {
          widget.onFilesDropped(paths);
        }
      },
      child: LayoutBuilder(
        builder: (context, constraints) => Align(
          // 빈 화면에서는 정중앙보다 조금 위 — 아래 여백이 남아야 "놓을 자리"로 읽힌다.
          alignment: constraints.maxHeight < 220
              ? Alignment.center
              : const Alignment(0, -0.25),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 620),
            child: _card(
              context,
              compact: constraints.maxHeight < 220,
              child: constraints.maxHeight < 220
                  ? _compactContent(context)
                  : _tallContent(context),
            ),
          ),
        ),
      ),
    );
  }

  /// 점선 테두리 카드 — "여기에 놓는 자리"라는 드롭존 관용 표현.
  Widget _card(BuildContext context, {required Widget child, required bool compact}) {
    final colors = Theme.of(context).colorScheme;
    // 점선은 **바깥 경계**여야 한다. 안쪽에 그리면 흰 카드와 점선이 겹쳐 상자가
    // 두 겹으로 보인다(첫 시안에서 실제로 그렇게 나왔다).
    return AnimatedContainer(
      duration: const Duration(milliseconds: 150),
      decoration: BoxDecoration(
        color: _hovering ? AppTheme.tapeSoft : colors.surface,
        borderRadius: BorderRadius.circular(AppTheme.panelRadius),
      ),
      child: CustomPaint(
        foregroundPainter: _DashedBorderPainter(
          color: _hovering ? AppTheme.tapeDeep : AppTheme.dashedLine,
        ),
        child: Padding(
          // 목록이 있을 때는 띠처럼 얇아지므로 세로 여백을 줄인다 —
          // 28을 그대로 쓰면 안에 든 버튼이 잘린다.
          padding: EdgeInsets.symmetric(
            horizontal: 30,
            vertical: compact ? 14 : 28,
          ),
          child: child,
        ),
      ),
    );
  }

  Widget _tallContent(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const _SampleDocument(),
        const SizedBox(height: 24),
        Text('파일을 여기로 끌어다 놓으세요', style: textTheme.titleLarge),
        const SizedBox(height: 6),
        Text(
          '이름·주민등록번호·연락처를 찾아 가립니다',
          style: textTheme.bodyMedium?.copyWith(color: colors.onSurfaceVariant),
        ),
        const SizedBox(height: 14),
        const _LocalOnlyNote(),
        if (widget.onBrowse != null) ...[
          const SizedBox(height: 10),
          _browseButton(),
        ],
      ],
    );
  }

  Widget _compactContent(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.add, size: 20, color: Theme.of(context).colorScheme.primary),
        const SizedBox(width: 10),
        Flexible(
          child: Text(
            '파일을 더 끌어다 놓으세요',
            style: textTheme.titleMedium,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        if (widget.onBrowse != null) ...[
          const SizedBox(width: 8),
          _browseButton(),
        ],
      ],
    );
  }

  Widget _browseButton() => OutlinedButton(
        onPressed: widget.onBrowse,
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppTheme.controlRadius),
          ),
        ),
        child: const Text('파일 찾아보기'),
      );
}

/// 이 도구가 하는 일을 한 장면으로 보여주는 예시 문서.
/// 안에 든 값은 **전부 합성**이다 — 실제 개인정보가 아니다.
class _SampleDocument extends StatelessWidget {
  const _SampleDocument();

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colors = Theme.of(context).colorScheme;

    final isLight = Theme.of(context).brightness == Brightness.light;
    // 테두리 없이 **면**으로만 구분한다 — 테두리를 두르면 점선 상자 안에 또 상자가 생긴다.
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 16),
      decoration: BoxDecoration(
        color: isLight ? AppTheme.desk : AppTheme.deskDark,
        borderRadius: BorderRadius.circular(AppTheme.panelRadius - 4),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // "예시"라고 못박는다 — 파일명처럼 적으면 이미 불러온 파일로 오해할 수 있다.
          Text(
            '예시 문서',
            style: textTheme.labelSmall?.copyWith(color: colors.onSurfaceVariant),
          ),
          const SizedBox(height: 10),
          DefaultTextStyle.merge(
            style: textTheme.bodyMedium!,
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _SampleLine(
                  before: '고객 ',
                  redacted: '김민서',
                  after: ' 님이 배송 문의로 연락하셨습니다.',
                ),
                SizedBox(height: 8),
                _SampleLine(
                  before: '연락처 ',
                  redacted: '010-1234-5678',
                  after: ' · 본인 확인 완료',
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// 문장 한 줄 — 가운데 한 조각만 테이프로 덮인다.
class _SampleLine extends StatelessWidget {
  const _SampleLine({
    required this.before,
    required this.redacted,
    required this.after,
  });

  final String before;
  final String redacted;
  final String after;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Flexible(child: Text(before, overflow: TextOverflow.ellipsis)),
        RedactedText(redacted),
        Flexible(child: Text(after, overflow: TextOverflow.ellipsis)),
      ],
    );
  }
}

/// 이 제품의 핵심 주장 — 파일을 올리기 전에 보여야 의미가 있다.
class _LocalOnlyNote extends StatelessWidget {
  const _LocalOnlyNote();

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.lock_outline, size: 14, color: colors.onSurfaceVariant),
        const SizedBox(width: 6),
        Text(
          '처리는 이 PC에서만 이뤄집니다 · 파일이 밖으로 나가지 않습니다',
          style: Theme.of(context)
              .textTheme
              .bodySmall
              ?.copyWith(color: colors.onSurfaceVariant),
        ),
      ],
    );
  }
}

/// 둥근 사각형 점선 테두리.
class _DashedBorderPainter extends CustomPainter {
  const _DashedBorderPainter({required this.color});

  final Color color;

  static const strokeWidth = 1.5;
  static const dash = 7.0;
  static const gap = 6.0;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final path = Path()
      ..addRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(
            strokeWidth / 2,
            strokeWidth / 2,
            size.width - strokeWidth,
            size.height - strokeWidth,
          ),
          const Radius.circular(AppTheme.panelRadius),
        ),
      );

    for (final metric in path.computeMetrics()) {
      var distance = 0.0;
      while (distance < metric.length) {
        canvas.drawPath(metric.extractPath(distance, distance + dash), paint);
        distance += dash + gap;
      }
    }
  }

  @override
  bool shouldRepaint(_DashedBorderPainter oldDelegate) =>
      color != oldDelegate.color;
}
