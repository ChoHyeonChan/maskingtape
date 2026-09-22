// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import 'package:flutter/material.dart';

import '../models/detection.dart';
import '../models/file_task.dart';
import '../services/anonymizer.dart';
import '../services/batch_processor.dart';
import '../services/default_backend.dart';
import '../services/file_picker.dart';
import '../services/llm_status.dart';
import '../services/shell.dart';
import '../theme.dart';
import '../widgets/drop_zone.dart';
import '../widgets/llm_status_pill.dart';
import '../widgets/options_toolbar.dart';
import '../widgets/result_preview_dialog.dart';
import '../widgets/status_pill.dart';
import 'text_screen.dart';

/// 홈 화면의 두 모드 — 파일을 끌어다 놓는 일괄 처리와, 문장을 직접 넣는 텍스트 입력.
enum HomeMode { files, text }

/// 홈 화면 — 드롭된 파일 작업 목록 상태를 들고 배치 처리 흐름을 잇는다.
///
/// 텍스트 입력 모드([TextScreen])로 전환할 수 있고, 백엔드·옵션·LLM 상태는 두 모드가
/// 공유한다 — 모드를 오가도 선택한 전략이 그대로다.
class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    this.initialFiles = const [],
    this.anonymizer,
    this.pickFiles = pickTextFiles,
    this.checkLlmStatus,
  });

  /// 위젯 테스트에서 목록 상태를 주입하기 위한 초기값.
  final List<String> initialFiles;

  /// 비식별화 백엔드 — 비우면 [defaultAnonymizer], 테스트에선 가짜 구현 주입.
  /// const 생성자를 유지하려고 여기서 기본값을 만들지 않고 State에서 만든다.
  final Anonymizer? anonymizer;

  /// 파일 선택 대화상자 — 기본은 OS 대화상자, 테스트에선 가짜 주입.
  final Future<List<String>> Function() pickFiles;

  /// 로컬 LLM 상태 확인 — 비우면 실제 Ollama에 물어본다. 테스트에선 가짜 주입.
  /// pickFiles와 같은 함수 주입 방식으로 맞춰, 위젯 테스트가 소켓을 타지 않게 한다.
  final Future<LlmStatus> Function()? checkLlmStatus;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final List<FileTask> _tasks = [
    for (final path in widget.initialFiles) FileTask(path),
  ];
  late final Anonymizer _anonymizer = widget.anonymizer ?? defaultAnonymizer();
  late final Future<LlmStatus> Function() _checkLlmStatus =
      widget.checkLlmStatus ?? OllamaProbe().check;
  bool _running = false;
  bool _cancelRequested = false;
  AnonymizeOptions _options = const AnonymizeOptions();
  HomeMode _mode = HomeMode.files;
  LlmStatus _llmStatus = const LlmStatus.checking();

  @override
  void initState() {
    super.initState();
    _refreshLlmStatus();
  }

  /// 로컬 LLM 상태를 다시 확인한다. 확인 실패도 상태값으로 오므로 예외 처리가 없다.
  Future<void> _refreshLlmStatus() async {
    if (mounted) setState(() => _llmStatus = const LlmStatus.checking());
    final status = await _checkLlmStatus();
    if (mounted) setState(() => _llmStatus = status);
  }

  bool get _hasWaiting => _tasks.any((t) => t.status == FileTaskStatus.waiting);

  int get _finished => _tasks
      .where(
        (t) =>
            t.status == FileTaskStatus.done ||
            t.status == FileTaskStatus.failed,
      )
      .length;

  Future<void> _browse() async {
    final paths = await widget.pickFiles();
    if (paths.isNotEmpty) {
      _addFiles(paths);
    }
  }

  void _addFiles(List<String> paths) {
    setState(() {
      final known = _tasks.map((t) => t.path).toSet();
      for (final path in paths) {
        if (known.add(path)) {
          _tasks.add(FileTask(path));
        }
      }
    });
  }

  Future<void> _start() async {
    setState(() {
      _running = true;
      _cancelRequested = false;
    });
    await BatchProcessor(_anonymizer).processAll(
      _tasks,
      () {
        if (mounted) setState(() {});
      },
      options: _options,
      isCancelled: () => _cancelRequested,
    );
    if (mounted) {
      setState(() => _running = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 84,
        // 웹 헤더와 같은 구성 — 로고 이미지 + 한 줄 설명. 같은 PNG를 쓴다(#442).
        title: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Image.asset(
              'assets/maskingtape-logo-blue.png',
              height: 40,
              semanticLabel: '마스킹테이프',
              // 다크 모드에선 로고의 남색 글자가 바탕에 묻히므로 밝게 반전한다.
              color: Theme.of(context).brightness == Brightness.dark
                  ? Theme.of(context).colorScheme.onSurface
                  : null,
              colorBlendMode: BlendMode.srcIn,
            ),
            const SizedBox(height: 4),
            Text(
              '문서를 끌어다 놓으면 개인정보를 한 번에 가립니다.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
        actions: [
          // 파일 일괄 ↔ 텍스트 입력. 처리 중에는 화면을 바꾸지 못하게 잠근다.
          SegmentedButton<HomeMode>(
            segments: const [
              ButtonSegment(
                value: HomeMode.files,
                icon: Icon(Icons.folder_copy_outlined, size: 18),
                label: Text('파일 일괄'),
              ),
              ButtonSegment(
                value: HomeMode.text,
                icon: Icon(Icons.edit_note, size: 18),
                label: Text('텍스트 입력'),
              ),
            ],
            selected: {_mode},
            showSelectedIcon: false,
            onSelectionChanged: _running
                ? null
                : (s) => setState(() => _mode = s.first),
          ),
          const SizedBox(width: 12),
          // LLM 상태는 파일이 없을 때도 보여야 한다 — 파일을 올리기 전에 Ollama를
          // 켜야 하는지 알 수 있어야 의미가 있다(#245 리뷰 메모).
          LlmStatusPill(status: _llmStatus, onRefresh: _refreshLlmStatus),
          if (_mode == HomeMode.files && _tasks.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(left: 8),
              child: TextButton.icon(
                onPressed: _running ? null : () => setState(_tasks.clear),
                icon: const Icon(Icons.delete_sweep_outlined),
                label: const Text('목록 비우기'),
              ),
            ),
          const SizedBox(width: 28),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.fromLTRB(32, 4, 32, 32),
        child: _mode == HomeMode.text ? _textBody() : _filesBody(context),
      ),
    );
  }

  Widget _textBody() => TextScreen(
    anonymizer: _anonymizer,
    options: _options,
    onOptionsChanged: (o) => setState(() => _options = o),
    onLlmTurnedOn: _refreshLlmStatus,
  );

  Widget _filesBody(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(
          flex: _tasks.isEmpty ? 1 : 0,
          child: SizedBox(
            height: _tasks.isEmpty ? null : 76,
            child: DropZone(onFilesDropped: _addFiles, onBrowse: _browse),
          ),
        ),
        if (_tasks.isNotEmpty) ...[
          const SizedBox(height: 20),
          // 창이 좁으면 파일 수와 조작부가 두 줄로 나뉜다.
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            runSpacing: 12,
            children: [
              Text(
                '파일 ${_tasks.length}개',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              Wrap(
                spacing: 12,
                runSpacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                alignment: WrapAlignment.end,
                children: [
                  OptionsToolbar(
                    options: _options,
                    onChanged: (o) => setState(() => _options = o),
                    enabled: !_running,
                    onLlmTurnedOn: _refreshLlmStatus,
                  ),
                  FilledButton.icon(
                    onPressed: _running
                        ? (_cancelRequested
                              ? null
                              : () => setState(() => _cancelRequested = true))
                        : (_hasWaiting ? _start : null),
                    icon: Icon(_running ? Icons.stop : Icons.play_arrow),
                    label: Text(
                      _running
                          ? (_cancelRequested ? '취소 중…' : '취소')
                          : '비식별화 시작',
                    ),
                  ),
                ],
              ),
            ],
          ),
          if (_running) ...[
            const SizedBox(height: 14),
            // 진행률은 테이프가 깔리는 것으로 읽힌다 — 색이 테이프 색이다(theme).
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: _tasks.isEmpty ? null : _finished / _tasks.length,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              '$_finished / ${_tasks.length} 처리됨',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
          const SizedBox(height: 12),
          Expanded(
            child: Material(
              color: Theme.of(context).colorScheme.surface,
              clipBehavior: Clip.antiAlias,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(AppTheme.panelRadius),
                side: BorderSide(
                  color: Theme.of(context).colorScheme.outlineVariant,
                ),
              ),
              child: _FileList(tasks: _tasks),
            ),
          ),
        ],
      ],
    );
  }
}

/// 파일 작업 목록 — 상태 아이콘과 결과 요약을 한 줄씩 보여준다.
class _FileList extends StatelessWidget {
  const _FileList({required this.tasks});

  final List<FileTask> tasks;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      itemCount: tasks.length,
      separatorBuilder: (_, _) => const Divider(height: 1),
      itemBuilder: (context, index) => _FileTile(task: tasks[index]),
    );
  }
}

class _FileTile extends StatelessWidget {
  const _FileTile({required this.task});

  final FileTask task;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;

    final (Widget leading, String subtitle) = switch (task.status) {
      FileTaskStatus.waiting => (const Icon(Icons.schedule), task.path),
      FileTaskStatus.processing => (
        const SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
        '처리 중…',
      ),
      FileTaskStatus.done => (
        Icon(Icons.check_circle, color: colors.primary),
        '탐지 ${task.detections.length}건 — ${Detection.summarize(task.detections)}\n'
            '저장: ${task.outputPath} · 클릭하면 비교 미리보기',
      ),
      FileTaskStatus.failed => (
        Icon(Icons.error_outline, color: colors.error),
        '실패: ${task.error}',
      ),
    };

    final done = task.status == FileTaskStatus.done;
    return ListTile(
      leading: leading,
      title: Text(task.name),
      subtitle: Text(subtitle, maxLines: 2, overflow: TextOverflow.ellipsis),
      onTap: done
          ? () => showDialog<void>(
              context: context,
              builder: (_) => ResultPreviewDialog(task: task),
            )
          : null,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          StatusPill(status: task.status),
          if (done)
            IconButton(
              icon: const Icon(Icons.folder_open),
              tooltip: '저장 폴더 열기',
              onPressed: () => revealInExplorer(task.outputPath!),
            ),
        ],
      ),
    );
  }
}
