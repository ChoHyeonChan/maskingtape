import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/sample_texts.dart';
import '../models/detection.dart';
import '../services/anonymizer.dart';
import '../services/mask_applier.dart';
import '../widgets/detection_panel.dart';
import '../widgets/highlighted_text.dart';
import '../widgets/options_toolbar.dart';
import '../widgets/panel.dart';

/// 텍스트 입력 모드 — 웹 플레이그라운드처럼 문장을 직접 넣고 버튼으로 탐지·마스킹한다.
///
/// 파일 모드와 같은 백엔드([Anonymizer])와 옵션을 쓴다. 옵션 값은 부모(홈 화면)가
/// 들고 있어 모드를 오가도 유지되고, 결과가 떠 있는 상태에서 옵션을 바꾸면 그 자리에서
/// 다시 돌린다 — 웹이 전략을 바꾸면 결과가 즉시 바뀌는 것과 같은 경험을 준다.
class TextScreen extends StatefulWidget {
  const TextScreen({
    super.key,
    required this.anonymizer,
    required this.options,
    required this.onOptionsChanged,
    this.onLlmTurnedOn,
  });

  final Anonymizer anonymizer;
  final AnonymizeOptions options;
  final ValueChanged<AnonymizeOptions> onOptionsChanged;
  final VoidCallback? onLlmTurnedOn;

  /// 웹과 같은 입력 상한. CLI 자체엔 제한이 없지만 LLM 모드에선 길수록 느리다.
  static const maxLength = 100000;

  @override
  State<TextScreen> createState() => _TextScreenState();
}

class _TextScreenState extends State<TextScreen> {
  final _controller = TextEditingController();
  AnonymizeResult? _result;
  String? _error;
  bool _running = false;

  /// 결과 패널에서 원문(하이라이트)을 볼지 마스킹 결과를 볼지.
  bool _showOriginal = false;

  /// 사용자가 「보임」으로 바꾼 항목 — 결과 텍스트에서 원문 그대로 남긴다.
  /// 새 결과가 오면 비운다(항목 정체성이 바뀌므로).
  final Set<Detection> _exposed = {};

  /// 가명 전략은 코어만 값을 만들 수 있어 항목별 조정이 없다 — 웹과 같은 제약.
  bool get _canAdjust => MaskApplier.supports(widget.options.strategy);

  bool _isMasked(Detection d) => !_exposed.contains(d);

  /// 화면에 보이는 마스킹 결과. mask/label은 항목별 선택을 반영해 앱에서 치환하고,
  /// pseudonym은 코어가 준 결과를 그대로 쓴다. 전부 가림이면 코어 출력과 같다.
  String _displayText(AnonymizeResult result) => _canAdjust
      ? MaskApplier.apply(
          _controller.text,
          result.detections,
          strategy: widget.options.strategy,
          isMasked: _isMasked,
        )
      : result.maskedText;

  @override
  void initState() {
    super.initState();
    _controller.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(TextScreen old) {
    super.didUpdateWidget(old);
    // 결과가 떠 있는데 전략·LLM 옵션이 바뀌면 같은 문장으로 다시 돌린다.
    final changed =
        old.options.strategy != widget.options.strategy ||
        old.options.useLlm != widget.options.useLlm;
    if (changed && _result != null && !_running) {
      _run();
    }
  }

  bool get _hasText => _controller.text.trim().isNotEmpty;

  Future<void> _run() async {
    setState(() {
      _running = true;
      _error = null;
    });
    try {
      final result = await widget.anonymizer.anonymize(
        _controller.text,
        options: widget.options,
      );
      if (mounted) {
        setState(() {
          _result = result;
          _exposed.clear();
        });
      }
    } on AnonymizerException catch (e) {
      // 백엔드가 준 안내(Ollama 미실행 등)를 그대로 보여준다 — 덮어쓰면 원인이 가려진다.
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _running = false);
    }
  }

  void _reset() {
    setState(() {
      _controller.clear();
      _result = null;
      _error = null;
      _showOriginal = false;
      _exposed.clear();
    });
  }

  /// 결과를 닫고 같은 문장을 다시 편집한다.
  void _edit() => setState(() => _result = null);

  Future<void> _copyMasked() async {
    final result = _result;
    if (result == null) return;
    final masked = _displayText(result);
    await Clipboard.setData(ClipboardData(text: masked));
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('마스킹 결과를 복사했습니다')));
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Align(
          alignment: Alignment.centerRight,
          child: OptionsToolbar(
            options: widget.options,
            onChanged: widget.onOptionsChanged,
            enabled: !_running,
            onLlmTurnedOn: widget.onLlmTurnedOn,
          ),
        ),
        const SizedBox(height: 14),
        Expanded(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                flex: 3,
                child: result == null
                    ? _inputPanel(context)
                    : _resultPanel(context, result),
              ),
              const SizedBox(width: 16),
              Expanded(flex: 2, child: _detectionsPanel(context, result)),
            ],
          ),
        ),
      ],
    );
  }

  Widget _inputPanel(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    return Panel(
      title: '문서 입력',
      icon: Icons.notes_outlined,
      actions: [
        for (final sample in SampleText.all.take(2))
          OutlinedButton(
            onPressed: _running ? null : () => _controller.text = sample.text,
            child: Text(sample.label),
          ),
        MenuAnchor(
          menuChildren: [
            for (final sample in SampleText.all)
              MenuItemButton(
                onPressed: () => _controller.text = sample.text,
                child: Text(sample.label),
              ),
          ],
          builder: (context, menu, _) => OutlinedButton.icon(
            onPressed: _running
                ? null
                : () => menu.isOpen ? menu.close() : menu.open(),
            icon: const Icon(Icons.expand_more, size: 18),
            label: const Text('샘플 더 불러오기'),
          ),
        ),
      ],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              enabled: !_running,
              maxLines: null,
              expands: true,
              textAlignVertical: TextAlignVertical.top,
              inputFormatters: [
                LengthLimitingTextInputFormatter(TextScreen.maxLength),
              ],
              decoration: const InputDecoration(
                hintText:
                    '예: 고객 홍길동님은 010-1234-5678 또는 hong@example.com으로 '
                    '연락 가능합니다.',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.all(14),
              ),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            '${_withCommas(_controller.text.length)} / '
            '${_withCommas(TextScreen.maxLength)}자',
            style: textTheme.bodySmall?.copyWith(
              color: colors.onSurfaceVariant,
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(
              _error!,
              style: textTheme.bodySmall?.copyWith(color: colors.error),
            ),
          ],
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                flex: 3,
                child: FilledButton.icon(
                  onPressed: _hasText && !_running ? _run : null,
                  icon: _running
                      ? const SizedBox.square(
                          dimension: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.search),
                  label: Text(
                    _running
                        ? '탐지 중…'
                        : _hasText
                        ? '개인정보 탐지 및 마스킹 하기'
                        : '텍스트 입력 필요',
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _hasText && !_running ? _reset : null,
                  icon: const Icon(Icons.refresh, size: 18),
                  label: const Text('초기화'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _resultPanel(BuildContext context, AnonymizeResult result) {
    return Panel(
      title: _showOriginal ? '원문 (탐지 하이라이트)' : '마스킹 결과',
      icon: Icons.notes_outlined,
      actions: [
        SegmentedButton<bool>(
          segments: const [
            ButtonSegment(value: false, label: Text('결과')),
            ButtonSegment(value: true, label: Text('원문')),
          ],
          selected: {_showOriginal},
          showSelectedIcon: false,
          onSelectionChanged: (s) => setState(() => _showOriginal = s.first),
        ),
        OutlinedButton.icon(
          onPressed: _copyMasked,
          icon: const Icon(Icons.copy_outlined, size: 18),
          label: const Text('결과 복사'),
        ),
        OutlinedButton.icon(
          onPressed: _edit,
          icon: const Icon(Icons.edit_outlined, size: 18),
          label: const Text('다시 입력'),
        ),
      ],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 옵션을 바꿔 다시 도는 동안엔 이전 결과가 남아 있으므로 진행 중임을 보인다.
          if (_running) ...[
            const LinearProgressIndicator(),
            const SizedBox(height: 8),
          ],
          Expanded(
            child: BorderedScroll(
              child: _showOriginal
                  ? HighlightedText(
                      text: _controller.text,
                      detections: result.detections,
                    )
                  : SelectableText(
                      _displayText(result),
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
            ),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: _reset,
            icon: const Icon(Icons.refresh),
            label: const Text('초기화 하기'),
          ),
        ],
      ),
    );
  }

  Widget _detectionsPanel(BuildContext context, AnonymizeResult? result) {
    return DetectionPanel(
      detections: result?.detections,
      isMasked: _isMasked,
      toggleEnabled: _canAdjust,
      disabledNote: _canAdjust
          ? null
          : '가명처리는 같은 원본값을 항상 같은 그럴듯한 가짜 값으로 바꿔 문서의 구조와 '
                '맥락을 그대로 유지합니다. 이 모드에서는 항목별 가림·노출 조정을 지원하지 않습니다.',
      onToggle: (d, masked) => setState(() {
        if (masked) {
          _exposed.remove(d);
        } else {
          _exposed.add(d);
        }
      }),
    );
  }

  static String _withCommas(int n) => n.toString().replaceAllMapped(
    RegExp(r'(\d)(?=(\d{3})+$)'),
    (m) => '${m[1]},',
  );
}
