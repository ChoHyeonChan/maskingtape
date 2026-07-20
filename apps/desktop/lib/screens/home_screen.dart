import 'package:flutter/material.dart';

import '../models/detection.dart';
import '../models/file_task.dart';
import '../services/anonymizer.dart';
import '../services/batch_processor.dart';
import '../services/cli_anonymizer.dart';
import '../services/shell.dart';
import '../widgets/drop_zone.dart';
import '../widgets/result_preview_dialog.dart';

/// 홈 화면 — 드롭된 파일 작업 목록 상태를 들고 배치 처리 흐름을 잇는다.
class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    this.initialFiles = const [],
    this.anonymizer = const CliAnonymizer(),
  });

  /// 위젯 테스트에서 목록 상태를 주입하기 위한 초기값.
  final List<String> initialFiles;

  /// 비식별화 백엔드 — 기본은 core CLI, 테스트에선 가짜 구현 주입.
  final Anonymizer anonymizer;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final List<FileTask> _tasks = [
    for (final path in widget.initialFiles) FileTask(path),
  ];
  bool _running = false;
  bool _cancelRequested = false;
  MaskStrategy _strategy = MaskStrategy.mask;

  bool get _hasWaiting =>
      _tasks.any((t) => t.status == FileTaskStatus.waiting);

  int get _finished => _tasks
      .where((t) =>
          t.status == FileTaskStatus.done || t.status == FileTaskStatus.failed)
      .length;

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
    await BatchProcessor(widget.anonymizer).processAll(
      _tasks,
      () {
        if (mounted) setState(() {});
      },
      strategy: _strategy,
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
        title: const Text('마스킹테이프 — 문서 일괄 비식별화'),
        actions: [
          if (_tasks.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: TextButton.icon(
                onPressed: _running ? null : () => setState(_tasks.clear),
                icon: const Icon(Icons.delete_sweep_outlined),
                label: const Text('목록 비우기'),
              ),
            ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              flex: _tasks.isEmpty ? 1 : 0,
              child: SizedBox(
                height: _tasks.isEmpty ? null : 160,
                child: DropZone(onFilesDropped: _addFiles),
              ),
            ),
            if (_tasks.isNotEmpty) ...[
              const SizedBox(height: 24),
              Row(
                children: [
                  Text(
                    '파일 ${_tasks.length}개',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const Spacer(),
                  SegmentedButton<MaskStrategy>(
                    segments: [
                      for (final s in MaskStrategy.values)
                        ButtonSegment(value: s, label: Text(s.displayName)),
                    ],
                    selected: {_strategy},
                    onSelectionChanged: _running
                        ? null
                        : (selection) =>
                            setState(() => _strategy = selection.first),
                  ),
                  const SizedBox(width: 12),
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
              if (_running) ...[
                const SizedBox(height: 12),
                LinearProgressIndicator(
                  value: _tasks.isEmpty ? null : _finished / _tasks.length,
                ),
                const SizedBox(height: 4),
                Text(
                  '$_finished / ${_tasks.length} 처리됨',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
              const SizedBox(height: 8),
              Expanded(child: _FileList(tasks: _tasks)),
            ],
          ],
        ),
      ),
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
      FileTaskStatus.waiting => (
          const Icon(Icons.schedule),
          task.path,
        ),
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
      trailing: done
          ? IconButton(
              icon: const Icon(Icons.folder_open),
              tooltip: '저장 폴더 열기',
              onPressed: () => revealInExplorer(task.outputPath!),
            )
          : null,
    );
  }
}
