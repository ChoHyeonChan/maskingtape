import 'package:flutter/material.dart';

import '../widgets/drop_zone.dart';

/// 홈 화면 — 드롭된 파일 목록 상태를 들고 드롭존과 목록을 배치한다.
/// 비식별화 처리 연결(core CLI 호출)은 다음 단계.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, this.initialFiles = const []});

  /// 위젯 테스트에서 목록 상태를 주입하기 위한 초기값.
  final List<String> initialFiles;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final List<String> _files = [...widget.initialFiles];

  void _addFiles(List<String> paths) {
    setState(() {
      for (final path in paths) {
        if (!_files.contains(path)) {
          _files.add(path);
        }
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('마스킹테이프 — 문서 일괄 비식별화'),
        actions: [
          if (_files.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: TextButton.icon(
                onPressed: () => setState(_files.clear),
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
              flex: _files.isEmpty ? 1 : 0,
              child: SizedBox(
                height: _files.isEmpty ? null : 180,
                child: DropZone(onFilesDropped: _addFiles),
              ),
            ),
            if (_files.isNotEmpty) ...[
              const SizedBox(height: 24),
              Text(
                '대기 중인 파일 ${_files.length}개',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Expanded(child: _FileList(files: _files)),
            ],
          ],
        ),
      ),
    );
  }
}

/// 드롭된 파일 목록 — 파일명과 전체 경로만 보여준다.
class _FileList extends StatelessWidget {
  const _FileList({required this.files});

  final List<String> files;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      itemCount: files.length,
      separatorBuilder: (_, _) => const Divider(height: 1),
      itemBuilder: (context, index) {
        final path = files[index];
        final name = path.split(RegExp(r'[\\/]')).last;
        return ListTile(
          leading: const Icon(Icons.description_outlined),
          title: Text(name),
          subtitle: Text(
            path,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        );
      },
    );
  }
}
