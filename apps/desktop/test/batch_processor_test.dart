import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'package:maskingtape_desktop/models/detection.dart';
import 'package:maskingtape_desktop/models/file_task.dart';
import 'package:maskingtape_desktop/services/batch_processor.dart';

import 'fakes.dart';

void main() {
  test('maskedPathFor: 확장자 앞에 _masked를 붙인다', () {
    expect(
      BatchProcessor.maskedPathFor(r'C:\docs\상담기록.txt'),
      r'C:\docs\상담기록_masked.txt',
    );
    expect(BatchProcessor.maskedPathFor('/tmp/데이터'), '/tmp/데이터_masked');
    // 폴더명에 점이 있어도 파일명 확장자만 본다.
    expect(BatchProcessor.maskedPathFor(r'C:\v1.2\노트'), r'C:\v1.2\노트_masked');
  });

  test('summarize: 종류별 개수를 한국어 라벨로 요약한다', () {
    const rrn = Detection(kind: 'rrn', start: 0, end: 1, text: 'x');
    const phone = Detection(kind: 'phone', start: 0, end: 1, text: 'x');
    expect(Detection.summarize([]), '탐지 없음');
    expect(Detection.summarize([rrn, phone, phone]), '주민번호 1 · 전화번호 2');
  });

  test('processAll: 읽기 → 비식별화 → _masked 저장 → done', () async {
    final dir = await Directory.systemTemp.createTemp('maskingtape_test');
    addTearDown(() => dir.delete(recursive: true));
    final input = File('${dir.path}${Platform.pathSeparator}입력.txt');
    await input.writeAsString('주민번호 800101-1234560 문의주세요');

    final task = FileTask(input.path);
    await const BatchProcessor(FakeAnonymizer()).processAll([task], () {});

    expect(task.status, FileTaskStatus.done);
    expect(task.outputPath, endsWith('입력_masked.txt'));
    expect(task.detections, hasLength(1));
    final saved = await File(task.outputPath!).readAsString();
    expect(saved, '주민번호 ************** 문의주세요');
  });

  test('processAll: 없는 파일은 failed가 되고 나머지는 계속 처리한다', () async {
    final dir = await Directory.systemTemp.createTemp('maskingtape_test');
    addTearDown(() => dir.delete(recursive: true));
    final ok = File('${dir.path}${Platform.pathSeparator}정상.txt');
    await ok.writeAsString('내용');

    final missing = FileTask('${dir.path}${Platform.pathSeparator}없음.txt');
    final good = FileTask(ok.path);
    await const BatchProcessor(FakeAnonymizer())
        .processAll([missing, good], () {});

    expect(missing.status, FileTaskStatus.failed);
    expect(missing.error, isNotNull);
    expect(good.status, FileTaskStatus.done);
  });

  test('processAll: 백엔드 오류는 failed로 기록된다', () async {
    final dir = await Directory.systemTemp.createTemp('maskingtape_test');
    addTearDown(() => dir.delete(recursive: true));
    final input = File('${dir.path}${Platform.pathSeparator}입력.txt');
    await input.writeAsString('내용');

    final task = FileTask(input.path);
    await const BatchProcessor(FailingAnonymizer()).processAll([task], () {});

    expect(task.status, FileTaskStatus.failed);
    expect(task.error, '테스트용 실패');
  });
}
