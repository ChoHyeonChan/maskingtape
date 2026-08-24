import { useEffect, useRef, useState } from "react";
import { scanText } from "../../api/scanClient";
import { EXTRACT_ERROR_MESSAGES, extractTextFromFile } from "../../lib/extractText";
import type { MaskMode } from "../../lib/masking";
import type { Detection, HighlightRange } from "../../types/detection";

const PLACEHOLDER = "예: 고객 홍길동님은 010-1234-5678 또는 hong@example.com으로 연락 가능합니다.";
const MAX_TEXT_LENGTH = 100_000;

const PRESETS: { label: string; text: string }[] = [
  {
    label: "고객 상담 기록",
    text: "마스킹테이프 도입 검토 고객인 홍길동님과 전화 상담을 진행했습니다. 연락처는 010-1234-5678 또는 hong@example.com이며, 테스트 문서에는 주민등록번호 800101-1234560과 배송지 서울특별시 강남구 테헤란로 123이 함께 포함되어 있었습니다.",
  },
  {
    label: "신청서 샘플",
    text: "신청자 김민수, 주민등록번호 800101-1234560, 주소 서울특별시 강남구 테헤란로 123, 카드번호 4111-1111-1111-1111",
  },
  {
    label: "근로계약서 발췌",
    text: "근로계약서(발췌)\n사용자(갑): 마스킹테이프 주식회사\n근로자(을) 성명 김소연님, 주민등록번호 950322-2345671\n주소: 서울특별시 마포구 월드컵로 120 101동 502호\n연락처: 010-9876-5432\n위 당사자는 다음과 같이 근로계약을 체결하며, 근무 개시일은 2026년 3월 1일로 한다.",
  },
  {
    label: "임대차계약서 발췌",
    text: "주택임대차계약서(발췌)\n임차인 성명 박지훈씨, 주민등록번호 880715-1234567\n연락처 010-2345-6789, 이메일 jihoon.park@example.com\n주소: 경기도 성남시 분당구 정자동 178-4 스카이빌라 302동 1104호\n임대인과 위와 같이 전세 계약을 체결하며, 계약기간은 2026년 4월 1일부터 2028년 3월 31일까지로 한다.",
  },
];

interface Props {
  text: string;
  hasResult: boolean;
  resultVersion: number;
  maskMode?: MaskMode;
  onMaskModeChange?: (mode: MaskMode) => void;
  onTextChange: (text: string) => void;
  onClear: () => void;
  onResult: (text: string, detections: Detection[]) => void;
  onRequestEdit?: () => void;
  highlight?: HighlightRange | null;
}

export function InputPanel({
  text,
  hasResult,
  resultVersion,
  maskMode = "mask",
  onMaskModeChange = () => {},
  onTextChange,
  onClear,
  onResult,
  onRequestEdit = () => {},
  highlight = null,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [presetsOpen, setPresetsOpen] = useState(false);
  const [revealingResult, setRevealingResult] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const highlightOverlayRef = useRef<HTMLPreElement>(null);
  const trimmedLength = text.trim().length;
  const isTooLong = text.length > MAX_TEXT_LENGTH;
  const canScan = trimmedLength > 0 && !isTooLong;

  // 오른쪽 "탐지 결과 조정" 패널에서 토글·일괄 조정을 바꿔도 이 텍스트가 바뀐다 — 두 패널이
  // 화면에서 멀리 떨어져 있어 그냥 두면 왼쪽이 바뀐 걸 못 알아채기 쉽다. 처음 스캔 결과가
  // 나올 때뿐 아니라 text 자체가 바뀔 때마다 같은 스윕을 다시 재생해 "여기 바뀌었다"를
  // 알려준다(#237 계승 — 토글이 실제로 반영되는 걸 시각적으로도 확인시켜 준다).
  useEffect(() => {
    if (!hasResult || resultVersion === 0) return;

    setRevealingResult(true);
    const timeout = window.setTimeout(() => setRevealingResult(false), 950);
    return () => window.clearTimeout(timeout);
  }, [hasResult, resultVersion, text]);

  // 강조 범위가 새로 생기면(항목에 마우스를 올리면), 그 부분이 지금 스크롤 밖에 있을 때만
  // 가운데로 스크롤해서 보여준다 — 이미 보이는데도 매번 움직이면 오히려 산만하다.
  useEffect(() => {
    if (!highlight || !hasResult) return;
    const textarea = textareaRef.current;
    const overlay = highlightOverlayRef.current;
    const mark = overlay?.querySelector("mark");
    if (!textarea || !overlay || !mark) return;

    const overlayRect = overlay.getBoundingClientRect();
    const markRect = mark.getBoundingClientRect();
    const isVisible = markRect.top >= overlayRect.top && markRect.bottom <= overlayRect.bottom;
    if (isVisible) return;

    const markTopWithinContent = markRect.top - overlayRect.top + overlay.scrollTop;
    const target = markTopWithinContent - textarea.clientHeight / 2 + markRect.height / 2;
    const max = textarea.scrollHeight - textarea.clientHeight;
    const clamped = Math.max(0, Math.min(target, max));
    textarea.scrollTo({ top: clamped, behavior: "smooth" });
  }, [highlight, hasResult]);

  async function handleScan() {
    if (hasResult) {
      handleClear();
      return;
    }
    if (!canScan) return;
    setLoading(true);
    setError(null);
    try {
      const { detections } = await scanText(text);
      onResult(text, detections);
    } catch (err) {
      setError(err instanceof Error ? err.message : "탐지 요청 중 알 수 없는 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  // 파일은 절대 서버로 올리지 않는다 — 브라우저에서 텍스트만 추출해 기존 입력창에 채워 넣고,
  // 이후 흐름(검토 → 스캔)은 직접 입력한 텍스트와 완전히 동일하게 탄다(#263).
  async function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (!file || hasResult) return;

    setExtracting(true);
    setError(null);
    const result = await extractTextFromFile(file);
    setExtracting(false);

    if (result.ok) {
      onTextChange(result.text);
      setCopied(false);
    } else {
      setError(EXTRACT_ERROR_MESSAGES[result.reason]);
    }
  }

  function handleFileInputChange(event: React.ChangeEvent<HTMLInputElement>) {
    void handleFiles(event.target.files);
    event.target.value = "";
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
    void handleFiles(event.dataTransfer.files);
  }

  function handleDragOver(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    if (!hasResult) setDragActive(true);
  }

  function handleDragLeave() {
    setDragActive(false);
  }

  function handlePreset(text: string) {
    onTextChange(text);
    setError(null);
    setCopied(false);
    setPresetsOpen(false);
  }

  function handleClear() {
    onClear();
    setError(null);
    setCopied(false);
  }

  async function handleCopy() {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  function handleSaveFile() {
    if (!text) return;
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "masked-result.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className={hasResult ? "input-panel input-panel--result" : "input-panel"}>
      <div className="input-panel__header">
        <h2 data-coach="masked-result"><span aria-hidden="true">▤</span> {hasResult ? "마스킹 결과" : "문서 입력"}</h2>
        {hasResult && (
          <div className="input-panel__header-actions">
            <div className="input-panel__mask-mode" role="group" aria-label="마스킹 방식 선택">
              <button
                type="button"
                className={`input-panel__mask-mode-btn${maskMode === "mask" ? " is-active" : ""}`}
                aria-pressed={maskMode === "mask"}
                onClick={() => onMaskModeChange("mask")}
              >
                별표
              </button>
              <button
                type="button"
                className={`input-panel__mask-mode-btn${maskMode === "label" ? " is-active" : ""}`}
                aria-pressed={maskMode === "label"}
                onClick={() => onMaskModeChange("label")}
              >
                라벨
              </button>
              <button
                type="button"
                className={`input-panel__mask-mode-btn${maskMode === "pseudonym" ? " is-active" : ""}`}
                aria-pressed={maskMode === "pseudonym"}
                onClick={() => onMaskModeChange("pseudonym")}
              >
                가명처리
              </button>
            </div>
            <button
              type="button"
              className="input-panel__copy-header"
              onClick={handleCopy}
              disabled={!text}
              aria-label={copied ? "복사됨" : "마스킹 결과 복사"}
              title={copied ? "복사됨" : "복사"}
            >
              <span className="copy-icon" aria-hidden="true" />
              <span>마스킹 결과 복사</span>
            </button>
            <button
              type="button"
              className="input-panel__copy-header"
              onClick={handleSaveFile}
              disabled={!text}
              aria-label="파일로 저장"
              data-tooltip="파일로 저장"
            >
              <span className="upload-icon upload-icon--save" aria-hidden="true" />
              <span>파일로 저장</span>
            </button>
            {copied && (
              <span className="input-panel__copy-toast input-panel__copy-toast--header" role="status">
                복사되었습니다
              </span>
            )}
          </div>
        )}
        <div className={hasResult ? "input-panel__tools input-panel__tools--hidden" : "input-panel__tools"}>
          <button type="button" className="input-panel__sample" onClick={() => handlePreset(PRESETS[1].text)}>
            신청서 샘플
          </button>
          <button
            type="button"
            className="input-panel__sample input-panel__sample--contract"
            onClick={() => handlePreset(PRESETS[2].text)}
          >
            계약서 예제
          </button>
          <details
            className="input-panel__presets"
            data-coach="presets"
            open={presetsOpen}
            onToggle={(event) => setPresetsOpen(event.currentTarget.open)}
          >
            <summary className="input-panel__presets-label">샘플 더 불러오기...</summary>
            <div className="input-panel__preset-list">
              {PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  className="input-panel__preset"
                  onClick={() => handlePreset(preset.text)}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </details>
          <button
            type="button"
            className="input-panel__upload"
            onClick={() => fileInputRef.current?.click()}
            disabled={extracting}
            aria-label={extracting ? "추출 중..." : "파일 업로드"}
            data-tooltip={extracting ? "추출 중..." : "파일 업로드"}
          >
            <span className="upload-icon" aria-hidden="true" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.pdf,text/plain,application/pdf"
            className="input-panel__file-input"
            onChange={handleFileInputChange}
            aria-label="txt 또는 텍스트 PDF 파일 업로드"
          />
        </div>
      </div>

      <div
        className={`input-panel__textarea-wrap${revealingResult ? " is-revealing" : ""}${dragActive ? " is-drag-over" : ""}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        {hasResult && (
          <pre className="input-panel__highlight-overlay" ref={highlightOverlayRef} aria-hidden="true">
            {highlight ? (
              <>
                {text.slice(0, highlight.start)}
                <mark style={{ "--highlight-color": highlight.color } as React.CSSProperties}>
                  {text.slice(highlight.start, highlight.end)}
                </mark>
                {text.slice(highlight.end)}
              </>
            ) : (
              text
            )}
          </pre>
        )}
        <textarea
          ref={textareaRef}
          className={revealingResult ? "is-text-revealing" : undefined}
          value={text}
          onChange={(event) => {
            onTextChange(event.target.value);
            if (error) setError(null);
            if (copied) setCopied(false);
          }}
          onScroll={(event) => {
            if (highlightOverlayRef.current) {
              highlightOverlayRef.current.scrollTop = event.currentTarget.scrollTop;
            }
          }}
          onClick={() => {
            // 결과 상태에서 이 박스를 클릭하면 다시 고쳐서 재탐지하고 싶다는 뜻으로
            // 보고, 원문(수정 가능한 입력 상태)으로 되돌린다 — "초기화 하기"와 달리
            // 입력했던 텍스트 자체는 지우지 않는다.
            if (hasResult) onRequestEdit();
          }}
          placeholder={PLACEHOLDER}
          rows={8}
          readOnly={hasResult}
          aria-label={hasResult ? "마스킹된 탐지 결과" : "탐지할 텍스트 입력"}
          aria-describedby={hasResult ? undefined : "input-meta"}
        />
        {revealingResult && (
          <pre className="input-panel__result-reveal" aria-hidden="true">
            {text}
          </pre>
        )}
        {dragActive && (
          <div className="input-panel__drop-hint" aria-hidden="true">
            여기에 놓아 txt · PDF 파일에서 텍스트를 불러옵니다
          </div>
        )}
      </div>

      {!hasResult && (
        <div className="input-panel__meta" id="input-meta">
          <span className={isTooLong ? "input-panel__count input-panel__count--over" : "input-panel__count"}>
            {text.length.toLocaleString()} / {MAX_TEXT_LENGTH.toLocaleString()}자
          </span>
          {isTooLong && (
            <span className="input-panel__limit" role="alert">
              입력 길이가 상한을 초과했습니다. {(text.length - MAX_TEXT_LENGTH).toLocaleString()}자를 줄여주세요.
            </span>
          )}
        </div>
      )}

      <div className="input-panel__actions">
        <button
          type="button"
          onClick={handleScan}
          disabled={loading || (!canScan && !hasResult)}
          data-coach="scan"
          className={`input-panel__primary${canScan && !loading && !hasResult ? " is-ready" : " is-static"}`}
        >
          <span aria-hidden="true">{hasResult ? "↻" : "⌕"}</span>
          {hasResult ? "초기화 하기" : loading ? "처리 중..." : canScan ? "개인정보 탐지 및 마스킹 하기" : "텍스트 입력 필요"}
        </button>
        {!hasResult && (
          <button type="button" className="input-panel__secondary" onClick={handleClear} disabled={!text && !error}>
            <span aria-hidden="true">↻</span>
            초기화
          </button>
        )}
      </div>

      {error && (
        <p className="input-panel__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
