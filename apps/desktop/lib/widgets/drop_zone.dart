import 'package:desktop_drop/desktop_drop.dart';
import 'package:flutter/material.dart';

/// OS 파일 드래그&드롭을 받는 영역.
/// 받은 파일의 경로 목록을 콜백으로 넘기기만 하고, 목록 관리는 화면이 한다.
class DropZone extends StatefulWidget {
  const DropZone({super.key, required this.onFilesDropped});

  final ValueChanged<List<String>> onFilesDropped;

  @override
  State<DropZone> createState() => _DropZoneState();
}

class _DropZoneState extends State<DropZone> {
  bool _hovering = false;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

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
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        width: double.infinity,
        decoration: BoxDecoration(
          color:
              _hovering ? colors.primaryContainer : colors.surfaceContainerLow,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: _hovering ? colors.primary : colors.outlineVariant,
            width: 2,
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.upload_file_outlined, size: 72, color: colors.primary),
            const SizedBox(height: 16),
            Text('파일을 여기로 끌어다 놓으세요', style: textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(
              '여러 문서를 한 번에 비식별화합니다',
              style: textTheme.bodyMedium
                  ?.copyWith(color: colors.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }
}
