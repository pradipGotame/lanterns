import {
  useState,
  useRef,
  useCallback,
  useEffect,
  type CSSProperties,
} from "react";
import {
  FileText,
  FlaskConical,
  Code2,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Upload,
  Layers,
  Wifi,
  WifiOff,
  Trash2,
  ChevronRight,
  Sparkles,
  X,
  Database,
  Zap,
  ArrowLeft,
  Plus,
  RefreshCw,
  Minus,
  Equal,
  RotateCcw,
  ShieldAlert,
  Eraser,
  Download,
  FileJson,
  Braces,
  Moon,
  Sun,
} from "lucide-react";

// ── Embed types ───────────────────────────────────────────────────────────────

interface EmbedDiff {
  new: number;
  modified: number;
  deleted: number;
  unchanged: number;
}

interface EmbedJob {
  running: boolean;
  started_at: string | null;
  finished_at: string | null;
  phase: "deleted" | "modified" | "new" | null;
  total: number;
  done: number;
  errors: string[];
  last_file: string | null;
  diff: EmbedDiff;
}

interface EmbedFileStatus {
  id: string;
  name: string;
  category: string;
  indexed: boolean;
  change: "new" | "modified" | "unchanged";
}

interface EmbedStatus {
  job: EmbedJob;
  index: {
    total_vectors: number;
    dimension: number | null;
    by_category: Record<string, { vectors: number; unique_files: number }>;
  };
  files: EmbedFileStatus[];
  diff_preview: EmbedDiff;
}

interface LiveReportJob {
  running: boolean;
  done: boolean;
  error: string | null;
  progress: number;
  total: number;
  current: string | null;
  logs: string[];
  started_at: string | null;
  finished_at: string | null;
}

interface SavedReportSummary {
  exists: boolean;
  generated_at: string | null;
  total_requirements: number;
  total_rows: number;
  accepted: number;
  rejected: number;
  full: number;
  partial: number;
  weak: number;
  covered?: number;
  partially_covered?: number;
  not_covered?: number;
}

interface TraceReportStatus {
  job: LiveReportJob;
  saved: SavedReportSummary;
}

interface TraceabilityPromotedTestSummary {
  test_id: string;
  file: string;
  chunk_index: number | string;
  stage1_rank: number | string;
  score: number | string;
  rerank_score: number | string;
  safeguard_reason: string;
}

interface TraceabilityStage2Debug {
  rerank_input_tests: number;
  reranked_tests: number;
  safeguard_promoted_tests: TraceabilityPromotedTestSummary[];
  final_test_count: number;
}

interface TraceabilityVerifiedTest {
  test_id: string;
  test_file: string;
  test_chunk_index: number | string;
  line: number | string;
  verification_confidence: string;
  reasoning: string;
  matching_requirement_quotes: string[];
  assertion_evidence_lines: string[];
  retrieval_rank: number | string;
  rerank_score: number | string;
  test_chunk_text: string;
  safeguard_promoted: boolean;
  safeguard_reason?: string | null;
  stage1_rank?: number | string;
  score?: number | string;
}

interface TraceabilityImplementedBy {
  function: string | null;
  file: string | null;
  implementation_confidence: string;
  reasoning: string;
  source_id: string;
  source_file: string;
  source_chunk_index: number | string;
  retrieval_rank: number | string;
  rerank_score: number | string;
  source_chunk_text: string;
}

interface TraceabilitySupportingSource {
  source_id: string;
  source_file: string;
  source_chunk_index: number | string;
  retrieval_rank: number | string;
  rerank_score: number | string;
  source_chunk_text: string;
}

interface TraceabilityRequirementLevelResult {
  requirement_id: string;
  reasoning_preamble: string;
  evidence_inventory: {
    verified_by_tests: Array<{
      test_id: string;
      file: string | null;
      line: number;
      matching_requirement_quotes: string[];
      assertion_evidence_lines: string[];
      verification_confidence: string;
      reasoning: string;
    }>;
    implemented_by: Array<{
      function: string | null;
      file: string | null;
      implementation_confidence: string;
      reasoning: string;
    }>;
  };
  gap_analysis: {
    gap_identified: boolean;
    missing_scenarios: Array<{
      behaviour: string;
      scenario: string;
      type: string;
      priority: string;
      priority_rationale: string;
    }>;
    gap_rationale: string | null;
  };
  final_verdict: string;
  global_confidence_score: number | null;
}

interface TraceabilityViewRequirement {
  requirement_id: string;
  requirement_file: string;
  requirement_chunk_index: number | string;
  requirement_text: string;
  traceability_verdict: string;
  requirement_reasoning: string;
  traceability_gap: boolean;
  traceability_gap_reason: string | null;
  verified_test_count: number;
  implemented_by_count: number;
  stage2_debug: TraceabilityStage2Debug;
  verified_tests: TraceabilityVerifiedTest[];
  implemented_by: TraceabilityImplementedBy[];
  supporting_sources: TraceabilitySupportingSource[];
  traceability_report?: TraceabilityRequirementLevelResult | null;
  generated_at: string | null;
}

interface TraceabilityReportView {
  meta: {
    generated_at?: string | null;
    total_requirements?: number;
    total_rows?: number;
  };
  requirements: TraceabilityViewRequirement[];
}

interface AssertionSavedSummary extends SavedReportSummary {
  traceability_generated_at: string | null;
  fresh: boolean;
}

interface AssertionStatus {
  job: LiveReportJob;
  saved: AssertionSavedSummary;
  dependency: {
    traceability_exists: boolean;
    traceability_generated_at: string | null;
    fresh: boolean;
  };
}

interface GeneratedTestFileSummary {
  filename: string;
  framework: string;
  language: string;
  requirement_ids: string[];
  gap_keys: string[];
  test_functions: Array<{
    function_name: string;
    requirement_ids: string[];
    gap_key: string;
  }>;
}

interface GeneratedTestsSavedSummary {
  exists: boolean;
  generated_at: string | null;
  traceability_generated_at: string | null;
  assertion_generated_at: string | null;
  total_gap_requirements: number;
  total_gap_groups: number;
  total_files: number;
  fresh: boolean;
  files: GeneratedTestFileSummary[];
  warnings: string[];
}

interface GeneratedTestsStatus {
  job: LiveReportJob;
  saved: GeneratedTestsSavedSummary;
  dependency: {
    assertion_exists: boolean;
    assertion_generated_at: string | null;
    fresh: boolean;
  };
}

// ── Types ─────────────────────────────────────────────────────────────────────

type SectionKey = "requirement" | "test" | "source";
type ThemeMode = "light" | "dark";
type ConfirmTone = "info" | "warning" | "danger";
type EmbedPanelConfirmAction =
  | "rerun-report"
  | "clear-report"
  | "rerun-assertion"
  | "clear-assertion"
  | "rerun-generated-tests"
  | "clear-generated-tests";

interface UploadedFile {
  id: string;
  name: string;
  category: SectionKey;
  size_bytes: number;
  uploaded_at: string;
  chunk_count: number;
  chunk_size: number;
  chunk_overlap: number;
  uploading?: boolean;
  error?: string;
}
type FileStore = Record<SectionKey, UploadedFile[]>;

// ── Config ────────────────────────────────────────────────────────────────────

const API =
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  "http://localhost:8000";

const SECTIONS = [
  {
    key: "requirement" as SectionKey,
    label: "Requirements",
    short: "REQ",
    desc: "Specs, user stories & acceptance criteria",
    hint: "Supports .txt .md .pdf .docx and more",
    Icon: FileText,
    grad: "linear-gradient(135deg,#6366f1,#8b5cf6)",
    glow: "rgba(99,102,241,.25)",
    border: "rgba(99,102,241,.35)",
    pill: { bg: "rgba(99,102,241,.15)", color: "#6366f1" },
    dot: "#4f46e5",
    iconBg: "rgba(99,102,241,.12)",
    iconColor: "#4f46e5",
  },
  {
    key: "test" as SectionKey,
    label: "Test Files",
    short: "TEST",
    desc: "Unit, integration & end-to-end tests",
    hint: "Supports .py .js .ts .java .go and more",
    Icon: FlaskConical,
    grad: "linear-gradient(135deg,#10b981,#34d399)",
    glow: "rgba(16,185,129,.25)",
    border: "rgba(16,185,129,.35)",
    pill: { bg: "rgba(16,185,129,.12)", color: "#10b981" },
    dot: "#059669",
    iconBg: "rgba(16,185,129,.12)",
    iconColor: "#059669",
  },
  {
    key: "source" as SectionKey,
    label: "Source Code",
    short: "SRC",
    desc: "Implementation files, modules & scripts",
    hint: "Supports .py .ts .go .rs .java and more",
    Icon: Code2,
    grad: "linear-gradient(135deg,#f59e0b,#fb923c)",
    glow: "rgba(245,158,11,.25)",
    border: "rgba(245,158,11,.35)",
    pill: { bg: "rgba(245,158,11,.12)", color: "#d97706" },
    dot: "#b45309",
    iconBg: "rgba(245,158,11,.1)",
    iconColor: "#b45309",
  },
] as const;

const EXT_COLORS: Record<string, string> = {
  py: "#2563eb",
  js: "#b45309",
  ts: "#2563eb",
  tsx: "#22d3ee",
  jsx: "#22d3ee",
  java: "#ea580c",
  go: "#059669",
  rs: "#f97316",
  cpp: "#7c3aed",
  c: "#7c3aed",
  md: "#475569",
  txt: "#475569",
  pdf: "#dc2626",
  json: "#059669",
  yaml: "#059669",
  yml: "#059669",
  sh: "#a3e635",
  rb: "#dc2626",
  cs: "#4f46e5",
  swift: "#ea580c",
  kt: "#7c3aed",
  php: "#4f46e5",
  html: "#ea580c",
  css: "#2563eb",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmtBytes = (n: number) =>
  n < 1024
    ? `${n} B`
    : n < 1_048_576
      ? `${(n / 1024).toFixed(1)} KB`
      : `${(n / 1_048_576).toFixed(2)} MB`;

const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

const tmpId = () =>
  `tmp_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
const fileExt = (name: string) => name.split(".").pop()?.toLowerCase() ?? "";
const extColor = (ext: string) => EXT_COLORS[ext] ?? "#475569";

// ── Grid background ───────────────────────────────────────────────────────────

function GridBg() {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundImage: `
        linear-gradient(rgba(0,0,0,.025) 1px,transparent 1px),
        linear-gradient(90deg,rgba(0,0,0,.025) 1px,transparent 1px)
      `,
        backgroundSize: "40px 40px",
        maskImage:
          "radial-gradient(ellipse 80% 60% at 50% 0%,black 40%,transparent 100%)",
        pointerEvents: "none",
        zIndex: 0,
      }}
    />
  );
}

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({
  value,
  label,
  color,
}: {
  value: number;
  label: string;
  color: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "10px 18px",
        gap: 2,
      }}
    >
      <span style={{ fontSize: 20, fontWeight: 700, color, lineHeight: 1 }}>
        {value}
      </span>
      <span
        style={{
          fontSize: 10,
          color: "#57606a",
          letterSpacing: ".06em",
          textTransform: "uppercase",
        }}
      >
        {label}
      </span>
    </div>
  );
}

function ExpandableTraceText({
  text,
  maxChars = 280,
  emptyLabel = "No text available.",
}: {
  text: string;
  maxChars?: number;
  emptyLabel?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const value = text.trim();
  const shouldTrim = value.length > maxChars;
  const visibleText =
    expanded || !shouldTrim ? value : `${value.slice(0, maxChars).trimEnd()}…`;

  return (
    <div style={{ display: "grid", gap: 8 }}>
      <div
        style={{
          whiteSpace: "pre-wrap",
          fontSize: 12,
          lineHeight: 1.6,
          color: value ? "#1f2937" : "#6b7280",
          background: "rgba(255,255,255,.78)",
          border: "1px solid rgba(0,0,0,.05)",
          borderRadius: 10,
          padding: "10px 12px",
        }}
      >
        {value || emptyLabel}
      </div>
      {shouldTrim && (
        <button
          onClick={() => setExpanded((prev) => !prev)}
          style={{
            alignSelf: "flex-start",
            border: "none",
            background: "transparent",
            color: "#4f46e5",
            fontSize: 11,
            fontWeight: 700,
            cursor: "pointer",
            padding: 0,
          }}
        >
          {expanded ? "Show less" : "Show full"}
        </button>
      )}
      {shouldTrim && !expanded && (
        <div style={{ fontSize: 10, color: "#6b7280" }}>Showing preview</div>
      )}
    </div>
  );
}

// ── Sidebar tab ───────────────────────────────────────────────────────────────

function SidebarTab({
  section,
  count,
  isActive,
  uploading,
  onClick,
}: {
  section: (typeof SECTIONS)[number];
  count: number;
  isActive: boolean;
  uploading: boolean;
  onClick: () => void;
}) {
  const { label, Icon, grad, glow, border, pill, iconBg, iconColor } = section;

  return (
    <button
      onClick={onClick}
      style={{
        width: "100%",
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "11px 12px",
        borderRadius: 12,
        border: "1px solid",
        borderColor: isActive ? border : "transparent",
        background: isActive ? `rgba(0,0,0,.04)` : "transparent",
        boxShadow: isActive ? `0 0 20px ${glow}` : "none",
        cursor: "pointer",
        transition: "all .2s",
        textAlign: "left",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Active left bar */}
      {isActive && (
        <div
          style={{
            position: "absolute",
            left: 0,
            top: "20%",
            bottom: "20%",
            width: 3,
            borderRadius: 2,
            background: grad,
            boxShadow: `0 0 8px ${glow}`,
          }}
        />
      )}

      {/* Icon */}
      <div
        style={{
          width: 34,
          height: 34,
          borderRadius: 10,
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: isActive ? iconBg : "rgba(0,0,0,.04)",
          transition: "background .2s",
        }}
      >
        <Icon size={16} style={{ color: isActive ? iconColor : "#57606a" }} />
      </div>

      {/* Label */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            fontSize: 13,
            fontWeight: 600,
            lineHeight: 1.3,
            color: isActive ? "#1f2328" : "#57606a",
            transition: "color .2s",
          }}
        >
          {label}
        </p>
        {count > 0 && (
          <p style={{ fontSize: 11, color: "#57606a", marginTop: 1 }}>
            {count} file{count !== 1 ? "s" : ""}
          </p>
        )}
      </div>

      {/* Badge */}
      {uploading ? (
        <Loader2
          size={13}
          style={{
            color: iconColor,
            animation: "spin 1s linear infinite",
            flexShrink: 0,
          }}
        />
      ) : count > 0 ? (
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            padding: "2px 8px",
            borderRadius: 20,
            flexShrink: 0,
            background: isActive ? pill.bg : "rgba(0,0,0,.06)",
            color: isActive ? pill.color : "#57606a",
          }}
        >
          {count}
        </span>
      ) : null}
    </button>
  );
}

// ── Drop zone ─────────────────────────────────────────────────────────────────

function DropZone({
  section,
  onFiles,
}: {
  section: (typeof SECTIONS)[number];
  onFiles: (f: File[]) => void;
}) {
  const [over, setOver] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  const { grad, glow, border, iconBg, iconColor, hint } = section;

  return (
    <div
      onClick={() => ref.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const files = Array.from(e.dataTransfer.files);
        if (files.length) onFiles(files);
      }}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 12,
        padding: "40px 24px",
        borderRadius: 16,
        cursor: "pointer",
        border: `2px dashed ${over ? border : "rgba(0,0,0,.07)"}`,
        background: over ? `rgba(0,0,0,.03)` : "transparent",
        boxShadow: over ? `inset 0 0 40px ${glow}` : "none",
        transition: "all .2s",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Radial glow */}
      {over && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: `radial-gradient(ellipse at center,${glow} 0%,transparent 70%)`,
            pointerEvents: "none",
          }}
        />
      )}

      {/* Icon */}
      <div
        style={{
          width: 52,
          height: 52,
          borderRadius: 16,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: over ? iconBg : "rgba(0,0,0,.05)",
          boxShadow: over ? `0 0 24px ${glow}` : "none",
          transition: "all .2s",
        }}
        className={over ? "" : "float"}
      >
        <Upload
          size={22}
          style={{
            color: over ? iconColor : "#374151",
            transition: "color .2s",
          }}
        />
      </div>

      <div style={{ textAlign: "center", position: "relative" }}>
        <p
          style={{
            fontSize: 14,
            fontWeight: 600,
            marginBottom: 4,
            background: over ? grad : "none",
            WebkitBackgroundClip: over ? "text" : undefined,
            WebkitTextFillColor: over ? "transparent" : "#57606a",
            color: over ? undefined : "#57606a",
          }}
        >
          {over ? "Release to upload" : "Drag & drop files here"}
        </p>
        <p style={{ fontSize: 12, color: "#374151" }}>
          or{" "}
          <span
            style={{
              background: grad,
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            click to browse
          </span>
        </p>
        <p style={{ fontSize: 11, color: "#1f2328", marginTop: 6 }}>{hint}</p>
      </div>

      <input
        ref={ref}
        type="file"
        multiple
        style={{ display: "none" }}
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          if (files.length) {
            onFiles(files);
            e.target.value = "";
          }
        }}
      />
    </div>
  );
}

// ── File row ──────────────────────────────────────────────────────────────────

function FileRow({
  file,
  onRemove,
}: {
  file: UploadedFile;
  onRemove: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  const ext = fileExt(file.name);
  const color = extColor(ext);

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="fade-up"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "12px 16px",
        borderBottom: "1px solid rgba(0,0,0,.04)",
        background: hovered ? "rgba(0,0,0,.02)" : "transparent",
        transition: "background .15s",
        position: "relative",
      }}
    >
      {/* Uploading shimmer overlay */}
      {file.uploading && (
        <div
          className="shimmer"
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            borderRadius: 0,
          }}
        />
      )}

      {/* Ext badge */}
      <div
        style={{
          width: 38,
          height: 38,
          borderRadius: 10,
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: `${color}18`,
          fontSize: 10,
          fontWeight: 800,
          letterSpacing: ".04em",
          color,
          border: `1px solid ${color}25`,
        }}
      >
        {ext ? ext.slice(0, 4).toUpperCase() : "?"}
      </div>

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            fontSize: 13,
            fontWeight: 500,
            color: "#374151",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            lineHeight: 1.3,
          }}
        >
          {file.name}
        </p>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            marginTop: 3,
          }}
        >
          {file.uploading && (
            <span
              style={{
                fontSize: 11,
                color: "#4f46e5",
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              <Loader2
                size={9}
                style={{ animation: "spin 1s linear infinite" }}
              />
              Chunking…
            </span>
          )}
          {file.error && (
            <span
              style={{
                fontSize: 11,
                color: "#dc2626",
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              <AlertCircle size={9} /> Failed to upload
            </span>
          )}
          {!file.uploading && !file.error && (
            <>
              <span style={{ fontSize: 11, color: "#374151" }}>
                {fmtBytes(file.size_bytes)}
              </span>
              <span style={{ color: "#1f2328" }}>·</span>
              <span
                style={{
                  fontSize: 11,
                  padding: "1px 6px",
                  borderRadius: 6,
                  background: "rgba(99,102,241,.12)",
                  color: "#4f46e5",
                  fontWeight: 500,
                }}
              >
                {file.chunk_count} chunks
              </span>
              <span style={{ color: "#1f2328" }}>·</span>
              <span style={{ fontSize: 11, color: "#374151" }}>
                {fmtTime(file.uploaded_at)}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Status / action */}
      <div
        style={{
          flexShrink: 0,
          width: 28,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {file.uploading && (
          <Loader2
            size={14}
            style={{ color: "#4f46e5", animation: "spin 1s linear infinite" }}
          />
        )}
        {file.error && <AlertCircle size={14} style={{ color: "#dc2626" }} />}
        {!file.uploading &&
          !file.error &&
          (hovered ? (
            <button
              onClick={onRemove}
              style={{
                width: 26,
                height: 26,
                borderRadius: 8,
                border: "none",
                cursor: "pointer",
                background: "rgba(248,113,113,.12)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "background .15s",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = "rgba(248,113,113,.22)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "rgba(248,113,113,.12)")
              }
            >
              <Trash2 size={12} style={{ color: "#dc2626" }} />
            </button>
          ) : (
            <CheckCircle2 size={14} style={{ color: "rgba(52,211,153,.5)" }} />
          ))}
      </div>
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({ section }: { section: (typeof SECTIONS)[number] }) {
  const { Icon, iconBg, iconColor, hint } = section;
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        textAlign: "center",
        gap: 12,
      }}
    >
      <div
        className="float"
        style={{
          width: 56,
          height: 56,
          borderRadius: 18,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: iconBg,
        }}
      >
        <Icon size={24} style={{ color: iconColor }} />
      </div>
      <div>
        <p
          style={{
            fontSize: 14,
            fontWeight: 500,
            color: "#57606a",
            marginBottom: 4,
          }}
        >
          No {section.label.toLowerCase()} uploaded yet
        </p>
        <p
          style={{
            fontSize: 12,
            color: "#374151",
            maxWidth: 260,
            margin: "0 auto",
            lineHeight: 1.6,
          }}
        >
          {hint}
        </p>
      </div>
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          padding: "6px 14px",
          borderRadius: 20,
          background: "rgba(0,0,0,.03)",
          border: "1px dashed rgba(0,0,0,.07)",
        }}
      >
        <Upload size={11} style={{ color: "#57606a" }} />
        <span style={{ fontSize: 11, color: "#57606a" }}>
          Drag files or click the zone above
        </span>
      </div>
    </div>
  );
}

function ActionConfirmDialog({
  open,
  title,
  subtitle,
  description,
  note,
  confirmLabel,
  tone,
  Icon,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  subtitle: string;
  description: string;
  note?: string;
  confirmLabel: string;
  tone: ConfirmTone;
  Icon: React.ElementType;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;

  const toneStyles = {
    info: {
      panelBorder: "rgba(99,102,241,.3)",
      iconBg: "rgba(99,102,241,.12)",
      iconBorder: "rgba(99,102,241,.25)",
      iconColor: "#4f46e5",
      noteBg: "rgba(99,102,241,.07)",
      noteBorder: "rgba(99,102,241,.2)",
      noteColor: "#6366f1",
      confirmBg: "linear-gradient(135deg,#6366f1,#4f46e5)",
      confirmColor: "#ffffff",
      confirmShadow: "0 0 20px rgba(99,102,241,.3)",
    },
    warning: {
      panelBorder: "rgba(245,158,11,.3)",
      iconBg: "rgba(245,158,11,.12)",
      iconBorder: "rgba(245,158,11,.25)",
      iconColor: "#b45309",
      noteBg: "rgba(245,158,11,.08)",
      noteBorder: "rgba(245,158,11,.22)",
      noteColor: "#b45309",
      confirmBg: "linear-gradient(135deg,#f59e0b,#d97706)",
      confirmColor: "#000000",
      confirmShadow: "0 0 20px rgba(245,158,11,.35)",
    },
    danger: {
      panelBorder: "rgba(239,68,68,.3)",
      iconBg: "rgba(248,113,113,.12)",
      iconBorder: "rgba(239,68,68,.25)",
      iconColor: "#dc2626",
      noteBg: "rgba(248,113,113,.08)",
      noteBorder: "rgba(239,68,68,.18)",
      noteColor: "#dc2626",
      confirmBg: "linear-gradient(135deg,#dc2626,#b91c1c)",
      confirmColor: "#ffffff",
      confirmShadow: "0 0 20px rgba(220,38,38,.3)",
    },
  } as const;
  const styles = toneStyles[tone];

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 110,
        background: "rgba(0,0,0,.7)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      onClick={onCancel}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 440,
          borderRadius: 18,
          background: "#ffffff",
          border: `1px solid ${styles.panelBorder}`,
          boxShadow: "0 24px 48px rgba(0,0,0,.6)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "22px 24px 16px",
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 12,
              flexShrink: 0,
              background: styles.iconBg,
              border: `1px solid ${styles.iconBorder}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon size={18} style={{ color: styles.iconColor }} />
          </div>
          <div>
            <p
              style={{
                fontSize: 15,
                fontWeight: 700,
                color: "#1f2328",
                lineHeight: 1.2,
              }}
            >
              {title}
            </p>
            <p style={{ fontSize: 12, color: "#57606a", marginTop: 2 }}>
              {subtitle}
            </p>
          </div>
        </div>

        <div style={{ padding: "0 24px 20px" }}>
          <p style={{ fontSize: 13, color: "#57606a", lineHeight: 1.7 }}>
            {description}
          </p>
          {note && (
            <div
              style={{
                marginTop: 14,
                padding: "10px 14px",
                borderRadius: 10,
                background: styles.noteBg,
                border: `1px solid ${styles.noteBorder}`,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <AlertCircle
                size={13}
                style={{ color: styles.noteColor, flexShrink: 0 }}
              />
              <p style={{ fontSize: 12, color: styles.noteColor }}>{note}</p>
            </div>
          )}
        </div>

        <div
          style={{
            padding: "14px 24px",
            borderTop: "1px solid rgba(0,0,0,.06)",
            display: "flex",
            gap: 10,
            justifyContent: "flex-end",
          }}
        >
          <button
            onClick={onCancel}
            style={{
              padding: "9px 18px",
              borderRadius: 10,
              border: "1px solid rgba(0,0,0,.08)",
              background: "transparent",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: 600,
              color: "#57606a",
            }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 7,
              padding: "9px 20px",
              borderRadius: 10,
              border: "none",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: 700,
              color: styles.confirmColor,
              background: styles.confirmBg,
              boxShadow: styles.confirmShadow,
            }}
          >
            <Icon size={13} /> {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Diff badge ────────────────────────────────────────────────────────────────

function DiffBadge({
  count,
  label,
  Icon,
  bg,
  color,
  border,
}: {
  count: number;
  label: string;
  Icon: React.ElementType;
  bg: string;
  color: string;
  border: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        padding: "7px 13px",
        borderRadius: 10,
        background: bg,
        border: `1px solid ${border}`,
        flex: 1,
        minWidth: 90,
      }}
    >
      <Icon size={12} style={{ color, flexShrink: 0 }} />
      <div>
        <p style={{ fontSize: 18, fontWeight: 700, color, lineHeight: 1 }}>
          {count}
        </p>
        <p
          style={{
            fontSize: 10,
            color,
            opacity: 0.7,
            textTransform: "uppercase" as const,
            letterSpacing: ".05em",
            marginTop: 2,
          }}
        >
          {label}
        </p>
      </div>
    </div>
  );
}

// ── Embed panel ───────────────────────────────────────────────────────────────

function EmbedPanel({ onBack }: { onBack: () => void }) {
  const [status, setStatus] = useState<EmbedStatus | null>(null);
  const [started, setStarted] = useState(false);
  const [purging, setPurging] = useState(false);
  const [confirmPurge, setConfirmPurge] = useState(false);
  const [clearingIndex, setClearingIndex] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const [confirmAction, setConfirmAction] =
    useState<EmbedPanelConfirmAction | null>(null);
  const [filesExpanded, setFilesExpanded] = useState(false);
  const [query] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Live report state ───────────────────────────────────────────────────────
  const [reportState, setReportState] = useState<TraceReportStatus | null>(
    null,
  );
  const [reportViewState, setReportViewState] =
    useState<TraceabilityReportView | null>(null);
  const [reportViewLoading, setReportViewLoading] = useState(false);
  const [reportViewExpanded, setReportViewExpanded] = useState(false);
  const [openRequirementIds, setOpenRequirementIds] = useState<string[]>([]);
  const [assertionState, setAssertionState] = useState<AssertionStatus | null>(
    null,
  );
  const [generatedTestsState, setGeneratedTestsState] =
    useState<GeneratedTestsStatus | null>(null);
  const reportPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const assertionPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const generatedTestsPollRef = useRef<ReturnType<typeof setInterval> | null>(
    null,
  );
  const logBoxRef = useRef<HTMLDivElement>(null);
  const assertionLogBoxRef = useRef<HTMLDivElement>(null);
  const generatedTestsLogBoxRef = useRef<HTMLDivElement>(null);

  // Poll status
  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/embed/status`);
      const d: EmbedStatus = await r.json();
      setStatus(d);
      if (!d.job.running && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } catch {
      /* offline */
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchReportStatus();
    fetchAssertionStatus();
    fetchGeneratedTestsStatus();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (reportPollRef.current) clearInterval(reportPollRef.current);
      if (assertionPollRef.current) clearInterval(assertionPollRef.current);
      if (generatedTestsPollRef.current)
        clearInterval(generatedTestsPollRef.current);
    };
  }, [fetchStatus]);

  const startEmbed = async () => {
    setStarted(true);
    await fetch(`${API}/api/embed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    pollRef.current = setInterval(fetchStatus, 1200);
    fetchStatus();
    fetchReportStatus();
    fetchAssertionStatus();
    fetchGeneratedTestsStatus();
  };

  const purgeAndRerun = async () => {
    setConfirmPurge(false);
    setPurging(true);
    setStarted(true);
    try {
      await fetch(`${API}/api/embed/purge`, { method: "POST" });
      pollRef.current = setInterval(fetchStatus, 1200);
      fetchStatus();
      fetchReportStatus();
      fetchAssertionStatus();
      fetchGeneratedTestsStatus();
    } finally {
      setPurging(false);
    }
  };

  const runSearch = async () => {
    if (!query.trim()) {
      setSearching(false);
      return;
    }
    setSearching(true);
    try {
      const r = await fetch(`${API}/api/embed/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: 50 }),
      });
      if (r.ok) setResults(await r.json());
    } finally {
      setSearching(false);
    }
  };

  const clearIndex = async () => {
    setConfirmClear(false);
    setClearingIndex(true);
    try {
      await fetch(`${API}/api/embed`, { method: "DELETE" });
      setStarted(false);
      await fetchStatus();
      await fetchReportStatus();
      await fetchAssertionStatus();
      await fetchGeneratedTestsStatus();
    } finally {
      setClearingIndex(false);
    }
  };

  const fetchReportStatus = async () => {
    try {
      const r = await fetch(`${API}/api/trace/report/status`);
      if (!r.ok) return;
      const data: TraceReportStatus = await r.json();
      setReportState(data);
      if (!data.saved.exists) {
        setReportViewState(null);
        setOpenRequirementIds([]);
      }
      // Auto-scroll log box
      if (logBoxRef.current) {
        logBoxRef.current.scrollTop = logBoxRef.current.scrollHeight;
      }
      if (!data.job.running) {
        if (reportPollRef.current) {
          clearInterval(reportPollRef.current);
          reportPollRef.current = null;
        }
        await fetchAssertionStatus();
      } else if (data.saved.exists) {
        await fetchAssertionStatus();
      }
    } catch {
      /* offline */
    }
  };

  const fetchReportView = useCallback(
    async (force = false) => {
      if (!force && reportViewState) return;
      setReportViewLoading(true);
      try {
        const r = await fetch(`${API}/api/trace/report/view`);
        if (!r.ok) {
          if (r.status === 404) {
            setReportViewState(null);
          }
          return;
        }
        const data: TraceabilityReportView = await r.json();
        setReportViewState(data);
      } finally {
        setReportViewLoading(false);
      }
    },
    [reportViewState],
  );

  const startReport = async (reuseSavedRerank = false) => {
    setReportViewState(null);
    setOpenRequirementIds([]);
    const r = await fetch(`${API}/api/trace/report/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        top_k_recall: 20,
        top_k_final: 5,
        reuse_saved_rerank: reuseSavedRerank,
      }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: "Failed to start" }));
      alert(`Error: ${err.detail}`);
      return;
    }
    await fetchReportStatus();
    await fetchAssertionStatus();
    await fetchGeneratedTestsStatus();
    reportPollRef.current = setInterval(fetchReportStatus, 1000);
  };

  const downloadReportFile = async () => {
    const r = await fetch(`${API}/api/trace/report/download`);
    if (!r.ok) {
      alert("Report not ready yet");
      return;
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "traceability_report.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadReportCsv = async () => {
    const r = await fetch(`${API}/api/trace/report/download/csv`);
    if (!r.ok) {
      alert("Report not ready yet");
      return;
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "traceability_report.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const clearReport = async () => {
    const r = await fetch(`${API}/api/trace/report`, { method: "DELETE" });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: "Failed to clear" }));
      alert(`Error: ${err.detail}`);
      return;
    }
    setReportViewState(null);
    setReportViewExpanded(false);
    setOpenRequirementIds([]);
    await fetchReportStatus();
    await fetchAssertionStatus();
    await fetchGeneratedTestsStatus();
  };

  const fetchAssertionStatus = async () => {
    try {
      const r = await fetch(`${API}/api/trace/assertion/status`);
      if (!r.ok) return;
      const data: AssertionStatus = await r.json();
      setAssertionState(data);
      if (assertionLogBoxRef.current) {
        assertionLogBoxRef.current.scrollTop =
          assertionLogBoxRef.current.scrollHeight;
      }
      if (!data.job.running) {
        if (assertionPollRef.current) {
          clearInterval(assertionPollRef.current);
          assertionPollRef.current = null;
        }
        await fetchGeneratedTestsStatus();
      } else if (data.saved.exists) {
        await fetchGeneratedTestsStatus();
      }
    } catch {
      /* offline */
    }
  };

  const startAssertion = async () => {
    const r = await fetch(`${API}/api/trace/assertion/start`, {
      method: "POST",
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: "Failed to start" }));
      alert(`Error: ${err.detail}`);
      return;
    }
    await fetchAssertionStatus();
    await fetchGeneratedTestsStatus();
    assertionPollRef.current = setInterval(fetchAssertionStatus, 1000);
  };

  const downloadAssertionFile = async () => {
    const r = await fetch(`${API}/api/trace/assertion/download`);
    if (!r.ok) {
      alert("Assertion report not ready yet");
      return;
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "assertion_report.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadAssertionCsv = async () => {
    const r = await fetch(`${API}/api/trace/assertion/download/csv`);
    if (!r.ok) {
      alert("Assertion report not ready yet");
      return;
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "assertion_report.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const clearAssertion = async () => {
    const r = await fetch(`${API}/api/trace/assertion`, { method: "DELETE" });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: "Failed to clear" }));
      alert(`Error: ${err.detail}`);
      return;
    }
    await fetchAssertionStatus();
    await fetchReportStatus();
    await fetchGeneratedTestsStatus();
  };

  const fetchGeneratedTestsStatus = async () => {
    try {
      const r = await fetch(`${API}/api/trace/tests/status`);
      if (!r.ok) return;
      const data: GeneratedTestsStatus = await r.json();
      setGeneratedTestsState(data);
      if (generatedTestsLogBoxRef.current) {
        generatedTestsLogBoxRef.current.scrollTop =
          generatedTestsLogBoxRef.current.scrollHeight;
      }
      if (!data.job.running && generatedTestsPollRef.current) {
        clearInterval(generatedTestsPollRef.current);
        generatedTestsPollRef.current = null;
      }
    } catch {
      /* offline */
    }
  };

  const startGeneratedTests = async () => {
    const r = await fetch(`${API}/api/trace/tests/start`, {
      method: "POST",
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: "Failed to start" }));
      alert(`Error: ${err.detail}`);
      return;
    }
    await fetchGeneratedTestsStatus();
    generatedTestsPollRef.current = setInterval(
      fetchGeneratedTestsStatus,
      1000,
    );
  };

  const downloadGeneratedTestsManifest = async () => {
    const r = await fetch(`${API}/api/trace/tests/download`);
    if (!r.ok) {
      alert("Generated test manifest not ready yet");
      return;
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "generated_tests_manifest.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadGeneratedTestFile = async (filename: string) => {
    const r = await fetch(
      `${API}/api/trace/tests/download/file/${encodeURIComponent(filename)}`,
    );
    if (!r.ok) {
      alert(`Generated test file ${filename} not ready yet`);
      return;
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const clearGeneratedTests = async () => {
    const r = await fetch(`${API}/api/trace/tests`, { method: "DELETE" });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: "Failed to clear" }));
      alert(`Error: ${err.detail}`);
      return;
    }
    await fetchGeneratedTestsStatus();
    await fetchAssertionStatus();
  };

  const job = status?.job;
  const idx = status?.index;
  const reportJob = reportState?.job ?? null;
  const reportSaved = reportState?.saved ?? {
    exists: false,
    generated_at: null,
    total_requirements: 0,
    total_rows: 0,
    accepted: 0,
    rejected: 0,
    full: 0,
    partial: 0,
    weak: 0,
    covered: 0,
    partially_covered: 0,
    not_covered: 0,
  };
  const assertionJob = assertionState?.job ?? null;
  const assertionSaved = assertionState?.saved ?? {
    exists: false,
    generated_at: null,
    total_requirements: 0,
    total_rows: 0,
    accepted: 0,
    rejected: 0,
    full: 0,
    partial: 0,
    weak: 0,
    traceability_generated_at: null,
    fresh: false,
  };
  const assertionDependency = assertionState?.dependency ?? {
    traceability_exists: false,
    traceability_generated_at: null,
    fresh: false,
  };
  const generatedTestsJob = generatedTestsState?.job ?? null;
  const generatedTestsSaved = generatedTestsState?.saved ?? {
    exists: false,
    generated_at: null,
    traceability_generated_at: null,
    assertion_generated_at: null,
    total_gap_requirements: 0,
    total_gap_groups: 0,
    total_files: 0,
    fresh: false,
    files: [],
    warnings: [],
  };
  const generatedTestsDependency = generatedTestsState?.dependency ?? {
    assertion_exists: false,
    assertion_generated_at: null,
    fresh: false,
  };
  const traceabilityReady =
    assertionDependency.traceability_exists || reportSaved.exists;
  const assertionReadyForTests =
    generatedTestsDependency.assertion_exists || assertionSaved.exists;
  const reportViewGeneratedAt = reportViewState?.meta?.generated_at ?? null;
  const reportViewNeedsRefresh =
    reportSaved.exists && reportViewGeneratedAt !== reportSaved.generated_at;
  const diff = status?.diff_preview ?? {
    new: 0,
    modified: 0,
    deleted: 0,
    unchanged: 0,
  };
  const isRunning = job?.running ?? false;
  const isDone = started && !isRunning && (job?.finished_at ?? null) !== null;
  const progress =
    job && job.total > 0 ? Math.round((job.done / job.total) * 100) : 0;
  const totalVec = idx?.total_vectors ?? 0;

  useEffect(() => {
    if (!reportViewExpanded || !reportSaved.exists || reportJob?.running) {
      return;
    }
    if (!reportViewState || reportViewNeedsRefresh) {
      fetchReportView(reportViewNeedsRefresh);
    }
  }, [
    fetchReportView,
    reportJob?.running,
    reportSaved.exists,
    reportViewExpanded,
    reportViewNeedsRefresh,
    reportViewState,
  ]);

  // Work to do = new + modified + deleted
  const workItems = diff.new + diff.modified + diff.deleted;
  const allSynced = workItems === 0 && (status?.files ?? []).length > 0;
  const embeddingReadyForReport = allSynced || isDone;

  // Phase label during job run
  const phaseLabel: Record<string, string> = {
    deleted: "Removing deleted vectors",
    modified: "Re-embedding modified",
    new: "Embedding new files",
  };

  const catMeta: Record<string, { grad: string; glow: string }> = {
    requirement: {
      grad: "linear-gradient(135deg,#6366f1,#8b5cf6)",
      glow: "rgba(99,102,241,.4)",
    },
    test: {
      grad: "linear-gradient(135deg,#10b981,#34d399)",
      glow: "rgba(16,185,129,.4)",
    },
    source: {
      grad: "linear-gradient(135deg,#f59e0b,#fb923c)",
      glow: "rgba(245,158,11,.4)",
    },
  };

  // Change colour helpers for file rows
  const changeStyle = (change: EmbedFileStatus["change"], indexed: boolean) => {
    if (change === "new")
      return {
        bg: "rgba(99,102,241,.06)",
        border: "rgba(99,102,241,.2)",
        dot: "#4f46e5",
        label: "New",
        labelColor: "#6366f1",
        labelBg: "rgba(99,102,241,.15)",
      };
    if (change === "modified")
      return {
        bg: "rgba(245,158,11,.06)",
        border: "rgba(245,158,11,.2)",
        dot: "#b45309",
        label: "Modified",
        labelColor: "#d97706",
        labelBg: "rgba(245,158,11,.12)",
      };
    // unchanged / indexed
    return indexed
      ? {
          bg: "rgba(16,185,129,.04)",
          border: "rgba(16,185,129,.12)",
          dot: "#059669",
          label: "Synced",
          labelColor: "#10b981",
          labelBg: "rgba(16,185,129,.1)",
        }
      : {
          bg: "rgba(0,0,0,.02)",
          border: "rgba(0,0,0,.05)",
          dot: "#374151",
          label: "Pending",
          labelColor: "#57606a",
          labelBg: "rgba(0,0,0,.05)",
        };
  };

  const traceabilityVerdictTone = (verdict: string) => {
    if (verdict === "covered") {
      return {
        color: "#059669",
        bg: "rgba(16,185,129,.12)",
        border: "rgba(16,185,129,.2)",
      };
    }
    if (verdict === "partially_covered") {
      return {
        color: "#d97706",
        bg: "rgba(245,158,11,.12)",
        border: "rgba(245,158,11,.2)",
      };
    }
    return {
      color: "#dc2626",
      bg: "rgba(248,113,113,.08)",
      border: "rgba(239,68,68,.18)",
    };
  };

  const verificationConfidenceTone = (confidence: string) => {
    if (confidence === "full" || confidence === "high") {
      return {
        color: "#059669",
        bg: "rgba(16,185,129,.12)",
        border: "rgba(16,185,129,.18)",
      };
    }
    if (confidence === "partial" || confidence === "medium") {
      return {
        color: "#d97706",
        bg: "rgba(245,158,11,.12)",
        border: "rgba(245,158,11,.18)",
      };
    }
    if (confidence === "weak" || confidence === "low") {
      return {
        color: "#dc2626",
        bg: "rgba(248,113,113,.08)",
        border: "rgba(239,68,68,.18)",
      };
    }
    return {
      color: "#6b7280",
      bg: "rgba(107,114,128,.1)",
      border: "rgba(107,114,128,.18)",
    };
  };

  const confirmActionConfig =
    confirmAction === "rerun-report"
      ? {
          title: "Re-run traceability report",
          subtitle: "Regenerates the saved report from the current index",
          description:
            "This will run traceability analysis again, replace the currently saved report, and refresh the coverage verdicts for every requirement.",
          note:
            "Uploaded files and indexed vectors stay in place. Only the saved report output is replaced.",
          confirmLabel: "Proceed and re-run",
          tone: "info" as const,
          Icon: RefreshCw,
          run: () => startReport(true),
        }
      : confirmAction === "clear-report"
        ? {
            title: "Clear traceability report",
            subtitle: "Deletes the saved report output",
            description:
              "This will remove the saved traceability report and its expanded report view from the backend. Your uploaded files and vector index will remain untouched.",
            note:
              "Assertion and generated-test outputs may need to be re-run after the traceability report is recreated.",
            confirmLabel: "Proceed and clear",
            tone: "danger" as const,
            Icon: Eraser,
            run: clearReport,
          }
        : confirmAction === "rerun-assertion"
          ? {
              title: "Re-run assertion analysis",
              subtitle:
                "Recomputes assertion coverage from current traceability data",
              description:
                "This will run the assertion analysis again and replace the currently saved assertion report using the latest traceability results.",
              note:
                "Uploaded files, vectors, and the traceability report stay in place. Only the saved assertion output is refreshed.",
              confirmLabel: "Proceed and re-run",
              tone: "info" as const,
              Icon: RefreshCw,
              run: startAssertion,
            }
          : confirmAction === "clear-assertion"
            ? {
                title: "Clear assertion report",
                subtitle: "Deletes the saved assertion output",
                description:
                  "This will remove the saved assertion report from the backend. It does not delete uploaded files, embeddings, or the traceability report.",
                note:
                  "Generated tests that depend on this report may become stale or unavailable until assertion analysis is run again.",
                confirmLabel: "Proceed and clear",
                tone: "danger" as const,
                Icon: Eraser,
                run: clearAssertion,
              }
            : confirmAction === "rerun-generated-tests"
              ? {
                  title: "Re-run generated tests",
                  subtitle:
                    "Rebuilds saved generated test artifacts from current gaps",
                  description:
                    "This will generate the test manifest and downloadable test files again from the current assertion gaps, replacing the previously saved generated-test output.",
                  note:
                    "The source uploads and reports stay untouched. Only the generated test artifacts are replaced.",
                  confirmLabel: "Proceed and generate",
                  tone: "info" as const,
                  Icon: RefreshCw,
                  run: startGeneratedTests,
                }
              : confirmAction === "clear-generated-tests"
                ? {
                    title: "Clear generated tests",
                    subtitle: "Deletes the saved generated test artifacts",
                    description:
                      "This will remove the saved generated test manifest and downloadable generated test files from the backend. The assertion and traceability reports will remain available.",
                    note:
                      "You can generate the test artifacts again later without re-uploading files.",
                    confirmLabel: "Proceed and clear",
                    tone: "danger" as const,
                    Icon: Eraser,
                    run: clearGeneratedTests,
                  }
                : null;

  const handleConfirmAction = async () => {
    const run = confirmActionConfig?.run;
    setConfirmAction(null);
    if (run) await run();
  };

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        minWidth: 0,
        overflowY: "auto",
      }}
    >
      {/* Header */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 28px",
          height: 64,
          flexShrink: 0,
          borderBottom: "1px solid rgba(0,0,0,.08)",
          backdropFilter: "blur(12px)",
          background: "rgba(246,248,250,.92)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button
            onClick={onBack}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "6px 12px",
              borderRadius: 8,
              border: "1px solid rgba(0,0,0,.07)",
              background: "transparent",
              cursor: "pointer",
              color: "#57606a",
              fontSize: 12,
              transition: "all .15s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "#57606a";
              e.currentTarget.style.borderColor = "rgba(0,0,0,.12)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "#57606a";
              e.currentTarget.style.borderColor = "rgba(0,0,0,.07)";
            }}
          >
            <ArrowLeft size={13} /> Back
          </button>
          <div
            style={{ width: 1, height: 20, background: "rgba(0,0,0,.07)" }}
          />
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 10,
              background: "rgba(99,102,241,.12)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 16px rgba(99,102,241,.2)",
            }}
          >
            <Database size={15} style={{ color: "#4f46e5" }} />
          </div>
          <div>
            <h1
              style={{
                fontSize: 14,
                fontWeight: 700,
                color: "#1f2328",
                lineHeight: 1.2,
              }}
            >
              Pipeline
            </h1>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Vector count badge */}
          {totalVec > 0 && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 14px",
                borderRadius: 20,
                background: "rgba(99,102,241,.12)",
                border: "1px solid rgba(99,102,241,.2)",
              }}
            >
              <div
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "#4f46e5",
                  boxShadow: "0 0 6px #818cf8",
                }}
              />
              <span style={{ fontSize: 12, fontWeight: 600, color: "#6366f1" }}>
                {totalVec.toLocaleString()} vectors indexed
              </span>
            </div>
          )}

          {/* Purge button */}
          {!isRunning && (
            <button
              onClick={() => setConfirmPurge(true)}
              disabled={purging}
              title="Wipe index and re-embed everything from scratch"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "6px 14px",
                borderRadius: 10,
                border: "1px solid rgba(248,113,113,.25)",
                background: "rgba(248,113,113,.08)",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: 600,
                color: "#ef4444",
                transition: "all .15s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(248,113,113,.16)";
                e.currentTarget.style.borderColor = "rgba(248,113,113,.45)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(248,113,113,.08)";
                e.currentTarget.style.borderColor = "rgba(248,113,113,.25)";
              }}
            >
              <RotateCcw size={12} />
              Purge &amp; Re-run
            </button>
          )}
        </div>
      </header>

      {/* ── Confirm purge modal ── */}
      {confirmPurge && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 100,
            background: "rgba(0,0,0,.7)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          onClick={() => setConfirmPurge(false)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: 420,
              borderRadius: 18,
              background: "#ffffff",
              border: "1px solid rgba(220,38,38,.3)",
              boxShadow:
                "0 0 60px rgba(248,113,113,.15), 0 24px 48px rgba(0,0,0,.6)",
              overflow: "hidden",
            }}
          >
            {/* Modal header */}
            <div
              style={{
                padding: "22px 24px 16px",
                display: "flex",
                alignItems: "center",
                gap: 12,
              }}
            >
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 12,
                  flexShrink: 0,
                  background: "rgba(248,113,113,.12)",
                  border: "1px solid rgba(248,113,113,.25)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <ShieldAlert size={18} style={{ color: "#dc2626" }} />
              </div>
              <div>
                <p
                  style={{
                    fontSize: 15,
                    fontWeight: 700,
                    color: "#1f2328",
                    lineHeight: 1.2,
                  }}
                >
                  Purge &amp; Re-run
                </p>
                <p style={{ fontSize: 12, color: "#57606a", marginTop: 2 }}>
                  This action cannot be undone
                </p>
              </div>
            </div>

            {/* Modal body */}
            <div style={{ padding: "0 24px 20px" }}>
              <p style={{ fontSize: 13, color: "#57606a", lineHeight: 1.7 }}>
                This will{" "}
                <span style={{ color: "#ef4444", fontWeight: 600 }}>
                  delete all {totalVec.toLocaleString()} vectors
                </span>{" "}
                from the Chroma index and clear all fingerprints, then
                immediately re-embed every uploaded file from scratch. Unchanged
                files will <em>not</em> be skipped — everything is rebuilt.
              </p>
              <div
                style={{
                  marginTop: 14,
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: "rgba(245,158,11,.07)",
                  border: "1px solid rgba(245,158,11,.2)",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <AlertCircle
                  size={13}
                  style={{ color: "#b45309", flexShrink: 0 }}
                />
                <p style={{ fontSize: 12, color: "#d97706" }}>
                  All search results will be unavailable until re-embedding
                  completes.
                </p>
              </div>
            </div>

            {/* Modal actions */}
            <div
              style={{
                padding: "14px 24px",
                borderTop: "1px solid rgba(0,0,0,.06)",
                display: "flex",
                gap: 10,
                justifyContent: "flex-end",
              }}
            >
              <button
                onClick={() => setConfirmPurge(false)}
                style={{
                  padding: "9px 18px",
                  borderRadius: 10,
                  border: "1px solid rgba(0,0,0,.08)",
                  background: "transparent",
                  cursor: "pointer",
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#57606a",
                }}
              >
                Cancel
              </button>
              <button
                onClick={purgeAndRerun}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 7,
                  padding: "9px 20px",
                  borderRadius: 10,
                  border: "none",
                  cursor: "pointer",
                  fontSize: 13,
                  fontWeight: 700,
                  color: "#fff",
                  background: "linear-gradient(135deg,#dc2626,#b91c1c)",
                  boxShadow: "0 0 20px rgba(220,38,38,.35)",
                }}
              >
                <RotateCcw size={13} /> Yes, purge &amp; re-run
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Confirm clear modal ── */}
      {confirmClear && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 100,
            background: "rgba(0,0,0,.7)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          onClick={() => setConfirmClear(false)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: 420,
              borderRadius: 18,
              background: "#ffffff",
              border: "1px solid rgba(180,83,9,.3)",
              boxShadow:
                "0 0 60px rgba(251,191,36,.12), 0 24px 48px rgba(0,0,0,.6)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                padding: "22px 24px 16px",
                display: "flex",
                alignItems: "center",
                gap: 12,
              }}
            >
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 12,
                  flexShrink: 0,
                  background: "rgba(251,191,36,.1)",
                  border: "1px solid rgba(251,191,36,.25)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Eraser size={18} style={{ color: "#b45309" }} />
              </div>
              <div>
                <p
                  style={{
                    fontSize: 15,
                    fontWeight: 700,
                    color: "#1f2328",
                    lineHeight: 1.2,
                  }}
                >
                  Clear Index
                </p>
                <p style={{ fontSize: 12, color: "#57606a", marginTop: 2 }}>
                  Removes vectors, does not re-embed
                </p>
              </div>
            </div>
            <div style={{ padding: "0 24px 20px" }}>
              <p style={{ fontSize: 13, color: "#57606a", lineHeight: 1.7 }}>
                This will{" "}
                <span style={{ color: "#d97706", fontWeight: 600 }}>
                  remove all {totalVec.toLocaleString()} vectors
                </span>{" "}
                from the Chroma index and clear all fingerprints. Your uploaded
                files remain untouched — you can re-embed them at any time.
              </p>
              <div
                style={{
                  marginTop: 14,
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: "rgba(99,102,241,.07)",
                  border: "1px solid rgba(99,102,241,.2)",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <AlertCircle
                  size={13}
                  style={{ color: "#4f46e5", flexShrink: 0 }}
                />
                <p style={{ fontSize: 12, color: "#6366f1" }}>
                  Search and traceability will be unavailable until you run a
                  new embedding job.
                </p>
              </div>
            </div>
            <div
              style={{
                padding: "14px 24px",
                borderTop: "1px solid rgba(0,0,0,.06)",
                display: "flex",
                gap: 10,
                justifyContent: "flex-end",
              }}
            >
              <button
                onClick={() => setConfirmClear(false)}
                style={{
                  padding: "9px 18px",
                  borderRadius: 10,
                  border: "1px solid rgba(0,0,0,.08)",
                  background: "transparent",
                  cursor: "pointer",
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#57606a",
                }}
              >
                Cancel
              </button>
              <button
                onClick={clearIndex}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 7,
                  padding: "9px 20px",
                  borderRadius: 10,
                  border: "none",
                  cursor: "pointer",
                  fontSize: 13,
                  fontWeight: 700,
                  color: "#000",
                  background: "linear-gradient(135deg,#f59e0b,#d97706)",
                  boxShadow: "0 0 20px rgba(245,158,11,.35)",
                }}
              >
                <Eraser size={13} /> Yes, clear index
              </button>
            </div>
          </div>
        </div>
      )}

      <ActionConfirmDialog
        open={confirmActionConfig !== null}
        title={confirmActionConfig?.title ?? ""}
        subtitle={confirmActionConfig?.subtitle ?? ""}
        description={confirmActionConfig?.description ?? ""}
        note={confirmActionConfig?.note}
        confirmLabel={confirmActionConfig?.confirmLabel ?? "Proceed"}
        tone={confirmActionConfig?.tone ?? "info"}
        Icon={confirmActionConfig?.Icon ?? AlertCircle}
        onConfirm={() => {
          void handleConfirmAction();
        }}
        onCancel={() => setConfirmAction(null)}
      />

      <div
        style={{
          flex: 1,
          padding: "28px",
          display: "flex",
          flexDirection: "column",
          gap: 20,
        }}
      >
        {/* ── Pre-run card ── */}
        {!started && (
          <div
            style={{
              border: "1px solid rgba(0,0,0,.06)",
              borderRadius: 16,
              background: "rgba(0,0,0,.02)",
              overflow: "hidden",
            }}
          >
            {/* Diff summary row */}
            {status && (
              <div
                style={{
                  padding: "16px 20px",
                  borderBottom: "1px solid rgba(0,0,0,.05)",
                }}
              >
                <p
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    color: "#374151",
                    textTransform: "uppercase",
                    letterSpacing: ".08em",
                    marginBottom: 10,
                  }}
                >
                  Change detection
                </p>
                <div
                  style={{ display: "flex", gap: 8, flexWrap: "wrap" as const }}
                >
                  <DiffBadge
                    count={diff.new}
                    label="New"
                    Icon={Plus}
                    bg="rgba(99,102,241,.08)"
                    color="#6366f1"
                    border="rgba(99,102,241,.2)"
                  />
                  <DiffBadge
                    count={diff.modified}
                    label="Modified"
                    Icon={RefreshCw}
                    bg="rgba(245,158,11,.08)"
                    color="#d97706"
                    border="rgba(245,158,11,.2)"
                  />
                  <DiffBadge
                    count={diff.deleted}
                    label="Deleted"
                    Icon={Minus}
                    bg="rgba(248,113,113,.08)"
                    color="#ef4444"
                    border="rgba(248,113,113,.2)"
                  />
                  <DiffBadge
                    count={diff.unchanged}
                    label="Unchanged"
                    Icon={Equal}
                    bg="rgba(16,185,129,.06)"
                    color="#10b981"
                    border="rgba(16,185,129,.15)"
                  />
                </div>

                {allSynced && (
                  <div
                    style={{
                      marginTop: 12,
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "8px 12px",
                      borderRadius: 10,
                      background: "rgba(16,185,129,.08)",
                      border: "1px solid rgba(16,185,129,.2)",
                    }}
                  >
                    <CheckCircle2 size={13} style={{ color: "#059669" }} />
                    <span style={{ fontSize: 12, color: "#10b981" }}>
                      All files are already up-to-date. Nothing to embed.
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Files list — collapsible */}
            <div style={{ borderBottom: "1px solid rgba(0,0,0,.05)" }}>
              {/* Clickable header row */}
              <button
                onClick={() => setFilesExpanded((v) => !v)}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "13px 20px",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  textAlign: "left",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.background = "rgba(0,0,0,.02)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background = "transparent")
                }
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: "#374151",
                      textTransform: "uppercase" as const,
                      letterSpacing: ".08em",
                    }}
                  >
                    Files
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: "1px 8px",
                      borderRadius: 20,
                      background: "rgba(0,0,0,.06)",
                      color: "#57606a",
                    }}
                  >
                    {(status?.files ?? []).length}
                  </span>
                </div>
                {/* Chevron */}
                <div
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: 6,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: "rgba(0,0,0,.04)",
                    transition: "transform .2s",
                    transform: filesExpanded
                      ? "rotate(180deg)"
                      : "rotate(0deg)",
                  }}
                >
                  <ChevronRight
                    size={12}
                    style={{ color: "#57606a", transform: "rotate(90deg)" }}
                  />
                </div>
              </button>

              {/* Collapsible body */}
              {filesExpanded && (
                <div
                  style={{
                    padding: "0 20px 14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 5,
                  }}
                >
                  {(status?.files ?? []).map((f) => {
                    const cs = changeStyle(f.change, f.indexed);
                    return (
                      <div
                        key={f.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          padding: "8px 12px",
                          borderRadius: 10,
                          background: cs.bg,
                          border: `1px solid ${cs.border}`,
                        }}
                      >
                        <div
                          style={{
                            width: 6,
                            height: 6,
                            borderRadius: "50%",
                            flexShrink: 0,
                            background: cs.dot,
                          }}
                        />
                        <span
                          style={{
                            flex: 1,
                            fontSize: 13,
                            color: "#57606a",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {f.name}
                        </span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 600,
                            padding: "2px 8px",
                            borderRadius: 20,
                            background: cs.labelBg,
                            color: cs.labelColor,
                            flexShrink: 0,
                          }}
                        >
                          {cs.label}
                        </span>
                      </div>
                    );
                  })}
                  {(status?.files ?? []).length === 0 && (
                    <p
                      style={{
                        fontSize: 13,
                        color: "#374151",
                        textAlign: "center",
                        padding: "12px 0",
                      }}
                    >
                      No files uploaded yet. Go back and upload files first.
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Action row */}
            <div
              style={{
                padding: "14px 20px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <p style={{ fontSize: 12, color: "#57606a" }}>
                Model:{" "}
                <span style={{ color: "#4f46e5" }}>
                  {import.meta.env.VITE_EMBED_MODEL ?? "text-embedding-3-small"}
                </span>
                <span style={{ margin: "0 6px", color: "#1f2328" }}>·</span>
                Store: <span style={{ color: "#4f46e5" }}>Chroma DB</span>
              </p>
              <button
                onClick={startEmbed}
                disabled={workItems === 0 && (status?.files ?? []).length > 0}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "10px 22px",
                  borderRadius: 12,
                  border: "none",
                  cursor: workItems > 0 ? "pointer" : "default",
                  fontSize: 13,
                  fontWeight: 700,
                  background:
                    workItems > 0
                      ? "linear-gradient(135deg,#4f46e5,#7c3aed)"
                      : "rgba(0,0,0,.05)",
                  color: workItems > 0 ? "#fff" : "#374151",
                  boxShadow:
                    workItems > 0 ? "0 0 24px rgba(99,102,241,.3)" : "none",
                  transition: "all .2s",
                }}
              >
                <Zap size={14} />
                {allSynced
                  ? "Already synced"
                  : `Embed ${workItems > 0 ? workItems : ""} file${workItems !== 1 ? "s" : ""}`}
              </button>
            </div>
          </div>
        )}

        {/* ── Progress card (after start) ── */}
        {started && (
          <div
            style={{
              border: "1px solid rgba(0,0,0,.06)",
              borderRadius: 16,
              background: "rgba(0,0,0,.02)",
              overflow: "hidden",
            }}
          >
            {/* Diff summary (from job state) */}
            {job?.diff && (
              <div
                style={{
                  padding: "14px 20px",
                  borderBottom: "1px solid rgba(0,0,0,.05)",
                }}
              >
                <div
                  style={{ display: "flex", gap: 8, flexWrap: "wrap" as const }}
                >
                  <DiffBadge
                    count={job.diff.new}
                    label="New"
                    Icon={Plus}
                    bg="rgba(99,102,241,.08)"
                    color="#6366f1"
                    border="rgba(99,102,241,.2)"
                  />
                  <DiffBadge
                    count={job.diff.modified}
                    label="Modified"
                    Icon={RefreshCw}
                    bg="rgba(245,158,11,.08)"
                    color="#d97706"
                    border="rgba(245,158,11,.2)"
                  />
                  <DiffBadge
                    count={job.diff.deleted}
                    label="Deleted"
                    Icon={Minus}
                    bg="rgba(248,113,113,.08)"
                    color="#ef4444"
                    border="rgba(248,113,113,.2)"
                  />
                  <DiffBadge
                    count={job.diff.unchanged}
                    label="Skipped"
                    Icon={Equal}
                    bg="rgba(16,185,129,.06)"
                    color="#10b981"
                    border="rgba(16,185,129,.15)"
                  />
                </div>
              </div>
            )}

            {/* Progress bar */}
            <div style={{ padding: "18px 20px 0" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: 10,
                }}
              >
                <span
                  style={{ fontSize: 13, fontWeight: 600, color: "#57606a" }}
                >
                  {isDone
                    ? "Indexing complete"
                    : isRunning && job?.phase
                      ? (phaseLabel[job.phase] ?? "Processing…")
                      : isRunning
                        ? `Processing ${job?.last_file ?? "…"}`
                        : "Preparing…"}
                </span>
                <span
                  style={{ fontSize: 12, color: "#4f46e5", fontWeight: 600 }}
                >
                  {progress}%
                </span>
              </div>
              <div
                style={{
                  height: 4,
                  borderRadius: 4,
                  background: "rgba(0,0,0,.06)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    borderRadius: 4,
                    background: "linear-gradient(90deg,#4f46e5,#7c3aed)",
                    width: `${progress}%`,
                    boxShadow: "0 0 12px rgba(99,102,241,.5)",
                    transition: "width .4s ease",
                  }}
                />
              </div>
              {job && job.total > 0 && (
                <p style={{ fontSize: 11, color: "#374151", marginTop: 8 }}>
                  {job.done} / {job.total} operations done
                  {job.last_file && isRunning && (
                    <span style={{ color: "#57606a" }}> · {job.last_file}</span>
                  )}
                </p>
              )}
            </div>

            {/* Per-category stats */}
            <div
              style={{
                display: "flex",
                gap: 1,
                padding: "16px 20px",
                flexWrap: "wrap" as const,
              }}
            >
              {Object.entries(idx?.by_category ?? {}).map(([cat, d]) => {
                const cm = catMeta[cat] ?? catMeta.requirement;
                return (
                  <div
                    key={cat}
                    style={{
                      flex: 1,
                      minWidth: 120,
                      padding: "12px 14px",
                      borderRadius: 12,
                      background: "rgba(0,0,0,.02)",
                      border: "1px solid rgba(0,0,0,.05)",
                      margin: 4,
                    }}
                  >
                    <p
                      style={{
                        fontSize: 20,
                        fontWeight: 700,
                        lineHeight: 1,
                        background: cm.grad,
                        WebkitBackgroundClip: "text",
                        WebkitTextFillColor: "transparent",
                      }}
                    >
                      {d.vectors.toLocaleString()}
                    </p>
                    <p
                      style={{
                        fontSize: 10,
                        color: "#57606a",
                        marginTop: 4,
                        textTransform: "uppercase" as const,
                        letterSpacing: ".06em",
                      }}
                    >
                      {cat} vectors
                    </p>
                    <p style={{ fontSize: 11, color: "#374151", marginTop: 2 }}>
                      {d.unique_files} file{d.unique_files !== 1 ? "s" : ""}
                    </p>
                  </div>
                );
              })}
            </div>

            {/* Errors */}
            {(job?.errors ?? []).length > 0 && (
              <div
                style={{
                  margin: "0 20px 16px",
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: "rgba(248,113,113,.08)",
                  border: "1px solid rgba(248,113,113,.2)",
                }}
              >
                {job!.errors.map((e, i) => (
                  <p
                    key={i}
                    style={{
                      fontSize: 12,
                      color: "#ef4444",
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                    }}
                  >
                    <AlertCircle size={11} /> {e}
                  </p>
                ))}
              </div>
            )}

            {/* Done banner */}
            {isDone && (
              <div style={{ padding: "0 20px 20px" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "10px 16px",
                    borderRadius: 12,
                    background: "rgba(16,185,129,.08)",
                    border: "1px solid rgba(16,185,129,.2)",
                  }}
                >
                  <CheckCircle2 size={15} style={{ color: "#059669" }} />
                  <span
                    style={{ fontSize: 13, fontWeight: 600, color: "#10b981" }}
                  >
                    {totalVec.toLocaleString()} vectors in Chroma ·{" "}
                    {job?.diff?.unchanged ?? 0} file
                    {(job?.diff?.unchanged ?? 0) !== 1 ? "s" : ""} skipped
                    (unchanged)
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Live Reports ── */}
        {totalVec > 0 && (
          <div
            style={{
              display: "grid",
              gap: 18,
            }}
          >
            <div
              style={{
                border: `1px solid ${reportJob?.error ? "rgba(248,113,113,.25)" : reportSaved.exists ? "rgba(16,185,129,.25)" : "rgba(99,102,241,.2)"}`,
                borderRadius: 16,
                background: "rgba(99,102,241,.03)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  padding: "14px 20px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  borderBottom: "1px solid rgba(0,0,0,.05)",
                  gap: 12,
                  flexWrap: "wrap" as const,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: 10,
                      flexShrink: 0,
                      background: "rgba(99,102,241,.12)",
                      border: "1px solid rgba(99,102,241,.2)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <FileJson size={16} style={{ color: "#4f46e5" }} />
                  </div>
                  <div>
                    <p
                      style={{
                        fontSize: 13,
                        fontWeight: 700,
                        color: "#57606a",
                        lineHeight: 1.3,
                      }}
                    >
                      Traceability Mapping
                    </p>
                    <p style={{ fontSize: 11, color: "#57606a", marginTop: 1 }}>
                      {reportJob?.running
                        ? `Processing ${reportJob.progress} / ${reportJob.total} requirements…`
                        : reportSaved.exists
                          ? `Saved ${reportSaved.total_requirements} requirements · ${reportSaved.total_rows} verified evidence rows`
                          : "Requirement-level traceability reports from the LLM"}
                    </p>
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    flexShrink: 0,
                    flexWrap: "wrap" as const,
                  }}
                >
                  {reportJob?.running && (
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 7,
                        padding: "8px 14px",
                        borderRadius: 10,
                        border: "1px solid rgba(99,102,241,.18)",
                        background: "rgba(99,102,241,.08)",
                        fontSize: 12,
                        fontWeight: 700,
                        color: "#4f46e5",
                      }}
                    >
                      <Loader2
                        size={13}
                        style={{ animation: "spin 1s linear infinite" }}
                      />
                      Running
                    </div>
                  )}
                  {!reportJob?.running && !reportSaved.exists && (
                    <button
                      onClick={() => startReport(false)}
                      disabled={!embeddingReadyForReport}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 7,
                        padding: "8px 18px",
                        borderRadius: 10,
                        border: "none",
                        cursor: embeddingReadyForReport
                          ? "pointer"
                          : "not-allowed",
                        fontSize: 12,
                        fontWeight: 700,
                        color: "#fff",
                        opacity: embeddingReadyForReport ? 1 : 0.5,
                        background: embeddingReadyForReport
                          ? "linear-gradient(135deg,#4f46e5,#7c3aed)"
                          : "rgba(107,114,128,.6)",
                        boxShadow: embeddingReadyForReport
                          ? "0 0 18px rgba(99,102,241,.3)"
                          : "none",
                      }}
                    >
                      <Zap size={13} /> Generate
                    </button>
                  )}
                  {!reportJob?.running && reportSaved.exists && (
                    <>
                      <button
                        onClick={() => setConfirmAction("rerun-report")}
                        title="Re-run traceability report"
                        aria-label="Re-run traceability report"
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "8px 14px",
                          borderRadius: 10,
                          border: "1px solid rgba(0,0,0,.08)",
                          background: "transparent",
                          cursor: "pointer",
                          fontSize: 12,
                          fontWeight: 600,
                          color: "#57606a",
                        }}
                      >
                        <RefreshCw size={12} />
                      </button>
                      <button
                        onClick={() => setConfirmAction("clear-report")}
                        title="Clear traceability report"
                        aria-label="Clear traceability report"
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "8px 14px",
                          borderRadius: 10,
                          border: "1px solid rgba(239,68,68,.25)",
                          background: "rgba(248,113,113,.06)",
                          cursor: "pointer",
                          fontSize: 12,
                          fontWeight: 700,
                          color: "#dc2626",
                        }}
                      >
                        <Eraser size={12} />
                      </button>
                      <button
                        onClick={downloadReportCsv}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 7,
                          padding: "8px 18px",
                          borderRadius: 10,
                          border: "1px solid rgba(99,102,241,.3)",
                          cursor: "pointer",
                          fontSize: 12,
                          fontWeight: 700,
                          color: "#4f46e5",
                          background: "rgba(99,102,241,.08)",
                        }}
                      >
                        <Download size={13} />
                      </button>
                      <button
                        onClick={downloadReportFile}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 7,
                          padding: "8px 18px",
                          borderRadius: 10,
                          border: "none",
                          cursor: "pointer",
                          fontSize: 12,
                          fontWeight: 700,
                          color: "#fff",
                          background: "linear-gradient(135deg,#10b981,#34d399)",
                          boxShadow: "0 0 16px rgba(16,185,129,.3)",
                        }}
                      >
                        <Braces size={13} />
                      </button>
                    </>
                  )}
                </div>
              </div>

              {reportJob?.running && (
                <div
                  style={{
                    padding: "10px 20px",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    borderBottom: "1px solid rgba(0,0,0,.04)",
                    background: "rgba(99,102,241,.04)",
                  }}
                >
                  <Loader2
                    size={13}
                    style={{
                      color: "#4f46e5",
                      animation: "spin 1s linear infinite",
                    }}
                  />
                  <span
                    style={{ fontSize: 12, color: "#374151", fontWeight: 600 }}
                  >
                    {reportJob.current ?? "Preparing traceability run…"}
                  </span>
                </div>
              )}

              {reportJob &&
                (reportJob.running || reportSaved.exists) &&
                reportJob.total > 0 && (
                  <div
                    style={{
                      padding: "10px 20px 0",
                      borderBottom: "1px solid rgba(0,0,0,.04)",
                    }}
                  >
                    <div
                      style={{
                        height: 3,
                        borderRadius: 3,
                        background: "rgba(0,0,0,.06)",
                        overflow: "hidden",
                        marginBottom: 8,
                      }}
                    >
                      <div
                        style={{
                          height: "100%",
                          borderRadius: 3,
                          background: reportJob.error
                            ? "#dc2626"
                            : reportSaved.exists && !reportJob.running
                              ? "linear-gradient(90deg,#10b981,#34d399)"
                              : "linear-gradient(90deg,#4f46e5,#7c3aed)",
                          width: `${Math.round((reportJob.progress / Math.max(reportJob.total, 1)) * 100)}%`,
                          transition: "width .5s ease",
                        }}
                      />
                    </div>
                  </div>
                )}

              {reportJob &&
                (reportJob.running ||
                  reportJob.logs.length > 0 ||
                  reportSaved.exists ||
                  !!reportJob.error) && (
                  <div
                    ref={logBoxRef}
                    style={{
                      maxHeight: 220,
                      overflowY: "auto",
                      padding: "10px 16px",
                      background: "rgba(0,0,0,.04)",
                      fontFamily: "monospace",
                      fontSize: 11,
                      lineHeight: 1.7,
                      borderTop: "1px solid rgba(0,0,0,.04)",
                    }}
                  >
                    {reportJob.logs.length === 0 && reportJob.running && (
                      <div
                        style={{
                          color: "#57606a",
                          whiteSpace: "pre-wrap" as const,
                        }}
                      >
                        Waiting for first pipeline log...
                      </div>
                    )}
                    {reportJob.logs.map((line, i) => {
                      const isError = line.startsWith("✗");
                      const isDone = line.startsWith("✓");
                      const isSep = line.startsWith("─");
                      const isLlmErr = line.includes("LLM ✗");
                      const isLlmOut = line.includes("LLM →");
                      const isLlmIn = line.includes("LLM ←");
                      const isStage3 = line.includes("Stage 3");
                      const isStage2 = line.includes("Stage 2");
                      const isStage1 = line.includes("Stage 1");
                      const color =
                        isError || isLlmErr
                          ? "#dc2626"
                          : isDone
                            ? "#059669"
                            : isSep
                              ? "#1f2328"
                              : isLlmOut
                                ? "#0f766e"
                                : isLlmIn
                                  ? "#0369a1"
                                  : isStage3
                                    ? "#f59e0b"
                                    : isStage2
                                      ? "#6366f1"
                                      : isStage1
                                        ? "#10b981"
                                        : "#57606a";
                      return (
                        <div
                          key={i}
                          style={{ color, whiteSpace: "pre-wrap" as const }}
                        >
                          {line}
                        </div>
                      );
                    })}
                    {reportJob.running && (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          color: "#4f46e5",
                          marginTop: 4,
                        }}
                      >
                        <Loader2
                          size={10}
                          style={{ animation: "spin 1s linear infinite" }}
                        />
                        <span>{reportJob.current ?? "Processing…"}</span>
                      </div>
                    )}
                  </div>
                )}

              {reportJob?.error && (
                <div
                  style={{
                    padding: "10px 20px",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    background: "rgba(248,113,113,.07)",
                    borderTop: "1px solid rgba(248,113,113,.15)",
                  }}
                >
                  <AlertCircle
                    size={13}
                    style={{ color: "#dc2626", flexShrink: 0 }}
                  />
                  <span style={{ fontSize: 12, color: "#ef4444" }}>
                    {reportJob.error}
                  </span>
                </div>
              )}

              {reportSaved.exists && !reportJob?.running && (
                <div
                  style={{
                    borderTop: "1px solid rgba(0,0,0,.05)",
                    background: "rgba(255,255,255,.42)",
                  }}
                >
                  <div
                    style={{
                      padding: "12px 16px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 12,
                      flexWrap: "wrap" as const,
                    }}
                  >
                    <div style={{ display: "grid", gap: 3 }}>
                      <span
                        style={{
                          fontSize: 12,
                          fontWeight: 700,
                          color: "#1f2937",
                        }}
                      >
                        Requirement and evidence chunks
                      </span>
                      <span style={{ fontSize: 11, color: "#6b7280" }}>
                        View requirement text, verified test evidence, and
                        supporting source chunks on demand.
                      </span>
                    </div>
                    <button
                      onClick={async () => {
                        const next = !reportViewExpanded;
                        setReportViewExpanded(next);
                        if (
                          next &&
                          reportSaved.exists &&
                          (!reportViewState || reportViewNeedsRefresh)
                        ) {
                          await fetchReportView(reportViewNeedsRefresh);
                        }
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 7,
                        padding: "8px 14px",
                        borderRadius: 10,
                        border: "1px solid rgba(99,102,241,.2)",
                        background: "rgba(99,102,241,.08)",
                        color: "#4f46e5",
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      {reportViewExpanded ? (
                        <Minus size={13} />
                      ) : (
                        <Plus size={13} />
                      )}
                      {reportViewExpanded ? "Hide Evidence" : "View Evidence"}
                    </button>
                  </div>

                  {reportViewExpanded && (
                    <div
                      style={{
                        padding: "0 16px 16px",
                        display: "grid",
                        gap: 12,
                      }}
                    >
                      {reportViewLoading && (
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                            padding: "12px 14px",
                            borderRadius: 12,
                            border: "1px solid rgba(99,102,241,.15)",
                            background: "rgba(99,102,241,.04)",
                            color: "#4f46e5",
                            fontSize: 12,
                            fontWeight: 600,
                          }}
                        >
                          <Loader2
                            size={13}
                            style={{ animation: "spin 1s linear infinite" }}
                          />
                          Loading saved traceability evidence…
                        </div>
                      )}

                      {!reportViewLoading &&
                        (reportViewState?.requirements?.length ?? 0) === 0 && (
                          <div
                            style={{
                              padding: "12px 14px",
                              borderRadius: 12,
                              border: "1px solid rgba(0,0,0,.05)",
                              background: "rgba(0,0,0,.03)",
                              color: "#6b7280",
                              fontSize: 12,
                            }}
                          >
                            No saved evidence details available yet.
                          </div>
                        )}

                      {!reportViewLoading &&
                        (reportViewState?.requirements ?? []).map((item) => {
                          const cardTone = traceabilityVerdictTone(
                            item.traceability_verdict,
                          );
                          const isOpen = openRequirementIds.includes(
                            item.requirement_id,
                          );
                          const promotedCount =
                            item.stage2_debug?.safeguard_promoted_tests
                              ?.length ?? 0;
                          return (
                            <div
                              key={item.requirement_id}
                              style={{
                                borderRadius: 14,
                                border: `1px solid ${cardTone.border}`,
                                background: "rgba(255,255,255,.76)",
                                overflow: "hidden",
                              }}
                            >
                              <button
                                onClick={() =>
                                  setOpenRequirementIds((prev) =>
                                    prev.includes(item.requirement_id)
                                      ? prev.filter(
                                          (id) => id !== item.requirement_id,
                                        )
                                      : [...prev, item.requirement_id],
                                  )
                                }
                                style={{
                                  width: "100%",
                                  border: "none",
                                  background: "transparent",
                                  cursor: "pointer",
                                  padding: "14px 16px",
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "space-between",
                                  gap: 12,
                                  textAlign: "left",
                                }}
                              >
                                <div
                                  style={{
                                    display: "grid",
                                    gap: 6,
                                    minWidth: 0,
                                  }}
                                >
                                  <div
                                    style={{
                                      display: "flex",
                                      alignItems: "center",
                                      gap: 8,
                                      flexWrap: "wrap" as const,
                                    }}
                                  >
                                    <span
                                      style={{
                                        fontSize: 13,
                                        fontWeight: 700,
                                        color: "#1f2937",
                                      }}
                                    >
                                      {item.requirement_id}
                                    </span>
                                    <span
                                      style={{
                                        padding: "3px 8px",
                                        borderRadius: 999,
                                        fontSize: 10,
                                        fontWeight: 800,
                                        letterSpacing: ".05em",
                                        textTransform: "uppercase",
                                        color: cardTone.color,
                                        background: cardTone.bg,
                                        border: `1px solid ${cardTone.border}`,
                                      }}
                                    >
                                      {item.traceability_verdict.replaceAll(
                                        "_",
                                        " ",
                                      )}
                                    </span>
                                  </div>
                                  <div
                                    style={{
                                      display: "flex",
                                      alignItems: "center",
                                      gap: 10,
                                      flexWrap: "wrap" as const,
                                      fontSize: 11,
                                      color: "#6b7280",
                                    }}
                                  >
                                    <span>
                                      Verified {item.verified_test_count} test
                                      {item.verified_test_count !== 1
                                        ? "s"
                                        : ""}
                                    </span>
                                    <span>
                                      Implemented by {item.implemented_by_count}
                                    </span>
                                    <span>
                                      Sources {item.supporting_sources.length}
                                    </span>
                                    <span>
                                      LLM confidence{" "}
                                      {item.traceability_report
                                        ?.global_confidence_score ?? "—"}
                                    </span>
                                    <span>
                                      Rerank input{" "}
                                      {item.stage2_debug?.rerank_input_tests ??
                                        0}
                                    </span>
                                    {promotedCount > 0 && (
                                      <span style={{ color: "#4f46e5" }}>
                                        Safeguard +{promotedCount}
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <ChevronRight
                                  size={15}
                                  style={{
                                    color: "#6b7280",
                                    transform: isOpen
                                      ? "rotate(90deg)"
                                      : "rotate(0deg)",
                                    transition: "transform .18s ease",
                                    flexShrink: 0,
                                  }}
                                />
                              </button>

                              {isOpen && (
                                <div
                                  style={{
                                    padding: "0 16px 16px",
                                    display: "grid",
                                    gap: 14,
                                    borderTop: "1px solid rgba(0,0,0,.05)",
                                  }}
                                >
                                  <div
                                    style={{
                                      display: "grid",
                                      gap: 6,
                                      paddingTop: 14,
                                    }}
                                  >
                                    <span
                                      style={{
                                        fontSize: 11,
                                        fontWeight: 700,
                                        color: "#374151",
                                        textTransform: "uppercase",
                                        letterSpacing: ".05em",
                                      }}
                                    >
                                      Requirement Chunk
                                    </span>
                                    <ExpandableTraceText
                                      text={item.requirement_text}
                                      maxChars={360}
                                      emptyLabel="Requirement chunk text missing."
                                    />
                                  </div>

                                  <div
                                    style={{
                                      display: "grid",
                                      gap: 6,
                                    }}
                                  >
                                    <span
                                      style={{
                                        fontSize: 11,
                                        fontWeight: 700,
                                        color: "#374151",
                                        textTransform: "uppercase",
                                        letterSpacing: ".05em",
                                      }}
                                    >
                                      Requirement Verdict Reasoning
                                    </span>
                                    <div
                                      style={{
                                        padding: "10px 12px",
                                        borderRadius: 10,
                                        background: cardTone.bg,
                                        border: `1px solid ${cardTone.border}`,
                                        color: "#374151",
                                        fontSize: 11,
                                        lineHeight: 1.5,
                                        whiteSpace: "pre-wrap",
                                      }}
                                    >
                                      {item.traceability_report
                                        ?.reasoning_preamble ||
                                        item.requirement_reasoning ||
                                        "No requirement-level reasoning saved."}
                                    </div>
                                  </div>

                                  {item.traceability_gap_reason && (
                                    <div
                                      style={{
                                        padding: "10px 12px",
                                        borderRadius: 10,
                                        background: "rgba(245,158,11,.08)",
                                        border:
                                          "1px solid rgba(245,158,11,.16)",
                                        color: "#92400e",
                                        fontSize: 11,
                                        lineHeight: 1.5,
                                      }}
                                    >
                                      {item.traceability_gap_reason}
                                    </div>
                                  )}

                                  <div style={{ display: "grid", gap: 10 }}>
                                    <span
                                      style={{
                                        fontSize: 11,
                                        fontWeight: 700,
                                        color: "#374151",
                                        textTransform: "uppercase",
                                        letterSpacing: ".05em",
                                      }}
                                    >
                                      Verified Test Evidence
                                    </span>
                                    {item.verified_tests.length === 0 && (
                                      <div
                                        style={{
                                          padding: "10px 12px",
                                          borderRadius: 10,
                                          background: "rgba(0,0,0,.03)",
                                          border: "1px solid rgba(0,0,0,.05)",
                                          fontSize: 11,
                                          color: "#6b7280",
                                        }}
                                      >
                                        No verified test evidence was saved for
                                        this requirement.
                                      </div>
                                    )}
                                    {item.verified_tests.map((test) => {
                                      const tone = verificationConfidenceTone(
                                        test.verification_confidence,
                                      );
                                      return (
                                        <div
                                          key={test.test_id}
                                          style={{
                                            display: "grid",
                                            gap: 10,
                                            padding: "12px",
                                            borderRadius: 12,
                                            border: `1px solid ${tone.border}`,
                                            background: "rgba(255,255,255,.78)",
                                          }}
                                        >
                                          <div
                                            style={{
                                              display: "flex",
                                              alignItems: "center",
                                              justifyContent: "space-between",
                                              gap: 10,
                                              flexWrap: "wrap" as const,
                                            }}
                                          >
                                            <div
                                              style={{
                                                display: "grid",
                                                gap: 4,
                                              }}
                                            >
                                              <span
                                                style={{
                                                  fontSize: 12,
                                                  fontWeight: 700,
                                                  color: "#1f2937",
                                                }}
                                              >
                                                {test.test_id}
                                              </span>
                                              <div
                                                style={{
                                                  display: "flex",
                                                  gap: 10,
                                                  flexWrap: "wrap" as const,
                                                  fontSize: 10,
                                                  color: "#6b7280",
                                                }}
                                              >
                                                <span>
                                                  line {test.line || "—"}
                                                </span>
                                                <span>
                                                  rank{" "}
                                                  {test.retrieval_rank || "—"}
                                                </span>
                                                <span>
                                                  rerank{" "}
                                                  {test.rerank_score || "—"}
                                                </span>
                                                {test.safeguard_promoted && (
                                                  <span
                                                    style={{ color: "#4f46e5" }}
                                                  >
                                                    safeguard promotion
                                                  </span>
                                                )}
                                                {test.stage1_rank && (
                                                  <span>
                                                    Stage 1 rank{" "}
                                                    {test.stage1_rank}
                                                  </span>
                                                )}
                                              </div>
                                            </div>
                                            <span
                                              style={{
                                                padding: "3px 8px",
                                                borderRadius: 999,
                                                fontSize: 10,
                                                fontWeight: 800,
                                                letterSpacing: ".05em",
                                                textTransform: "uppercase",
                                                color: tone.color,
                                                background: tone.bg,
                                                border: `1px solid ${tone.border}`,
                                              }}
                                            >
                                              {test.verification_confidence ||
                                                "—"}
                                            </span>
                                          </div>

                                          <ExpandableTraceText
                                            text={test.test_chunk_text}
                                            maxChars={320}
                                            emptyLabel="Test chunk text missing."
                                          />

                                          <div
                                            style={{
                                              padding: "10px 12px",
                                              borderRadius: 10,
                                              background: "rgba(0,0,0,.03)",
                                              border:
                                                "1px solid rgba(0,0,0,.05)",
                                              fontSize: 11,
                                              color: "#374151",
                                              lineHeight: 1.5,
                                              whiteSpace: "pre-wrap",
                                            }}
                                          >
                                            {test.reasoning ||
                                              "No reasoning saved."}
                                          </div>

                                          {test.matching_requirement_quotes
                                            .length > 0 && (
                                            <div
                                              style={{
                                                display: "grid",
                                                gap: 6,
                                              }}
                                            >
                                              <span
                                                style={{
                                                  fontSize: 10,
                                                  fontWeight: 700,
                                                  color: "#374151",
                                                  textTransform: "uppercase",
                                                  letterSpacing: ".05em",
                                                }}
                                              >
                                                Requirement Quotes
                                              </span>
                                              <div
                                                style={{
                                                  fontSize: 11,
                                                  color: "#4b5563",
                                                  lineHeight: 1.5,
                                                  whiteSpace: "pre-wrap",
                                                }}
                                              >
                                                {test.matching_requirement_quotes.join(
                                                  "\n",
                                                )}
                                              </div>
                                            </div>
                                          )}

                                          {test.assertion_evidence_lines
                                            .length > 0 && (
                                            <div
                                              style={{
                                                display: "grid",
                                                gap: 6,
                                              }}
                                            >
                                              <span
                                                style={{
                                                  fontSize: 10,
                                                  fontWeight: 700,
                                                  color: "#374151",
                                                  textTransform: "uppercase",
                                                  letterSpacing: ".05em",
                                                }}
                                              >
                                                Assertion Evidence
                                              </span>
                                              <div
                                                style={{
                                                  fontSize: 11,
                                                  color: "#4b5563",
                                                  lineHeight: 1.5,
                                                  whiteSpace: "pre-wrap",
                                                }}
                                              >
                                                {test.assertion_evidence_lines.join(
                                                  "\n",
                                                )}
                                              </div>
                                            </div>
                                          )}
                                        </div>
                                      );
                                    })}
                                  </div>

                                  <div style={{ display: "grid", gap: 10 }}>
                                    <span
                                      style={{
                                        fontSize: 11,
                                        fontWeight: 700,
                                        color: "#374151",
                                        textTransform: "uppercase",
                                        letterSpacing: ".05em",
                                      }}
                                    >
                                      Implementation Evidence
                                    </span>
                                    {item.implemented_by.length === 0 && (
                                      <div
                                        style={{
                                          padding: "10px 12px",
                                          borderRadius: 10,
                                          background: "rgba(0,0,0,.03)",
                                          border: "1px solid rgba(0,0,0,.05)",
                                          fontSize: 11,
                                          color: "#6b7280",
                                        }}
                                      >
                                        No implementation evidence was saved for
                                        this requirement.
                                      </div>
                                    )}
                                    {item.implemented_by.map((source) => (
                                      <div
                                        key={`${source.source_id}-${source.function || source.file || "source"}`}
                                        style={{
                                          display: "grid",
                                          gap: 10,
                                          padding: "12px",
                                          borderRadius: 12,
                                          border:
                                            "1px solid rgba(15,118,110,.14)",
                                          background: "rgba(255,255,255,.78)",
                                        }}
                                      >
                                        <div
                                          style={{
                                            display: "flex",
                                            alignItems: "center",
                                            justifyContent: "space-between",
                                            gap: 10,
                                            flexWrap: "wrap" as const,
                                          }}
                                        >
                                          <div
                                            style={{
                                              display: "grid",
                                              gap: 4,
                                            }}
                                          >
                                            <span
                                              style={{
                                                fontSize: 12,
                                                fontWeight: 700,
                                                color: "#1f2937",
                                              }}
                                            >
                                              {source.function ||
                                                source.file ||
                                                source.source_id}
                                            </span>
                                            <div
                                              style={{
                                                display: "flex",
                                                gap: 10,
                                                flexWrap: "wrap" as const,
                                                fontSize: 10,
                                                color: "#6b7280",
                                              }}
                                            >
                                              <span>
                                                file {source.source_file || "—"}
                                              </span>
                                              <span>
                                                rank{" "}
                                                {source.retrieval_rank || "—"}
                                              </span>
                                              <span>
                                                rerank{" "}
                                                {source.rerank_score || "—"}
                                              </span>
                                            </div>
                                          </div>
                                          <span
                                            style={{
                                              padding: "3px 8px",
                                              borderRadius: 999,
                                              fontSize: 10,
                                              fontWeight: 800,
                                              letterSpacing: ".05em",
                                              textTransform: "uppercase",
                                              color: "#0f766e",
                                              background:
                                                "rgba(13,148,136,.08)",
                                              border:
                                                "1px solid rgba(13,148,136,.15)",
                                            }}
                                          >
                                            {source.implementation_confidence ||
                                              "—"}
                                          </span>
                                        </div>

                                        <ExpandableTraceText
                                          text={source.source_chunk_text}
                                          maxChars={320}
                                          emptyLabel="Source chunk text missing."
                                        />

                                        <div
                                          style={{
                                            padding: "10px 12px",
                                            borderRadius: 10,
                                            background: "rgba(0,0,0,.03)",
                                            border: "1px solid rgba(0,0,0,.05)",
                                            fontSize: 11,
                                            color: "#374151",
                                            lineHeight: 1.5,
                                            whiteSpace: "pre-wrap",
                                          }}
                                        >
                                          {source.reasoning ||
                                            "No implementation reasoning saved."}
                                        </div>
                                      </div>
                                    ))}
                                  </div>

                                  <div style={{ display: "grid", gap: 10 }}>
                                    <span
                                      style={{
                                        fontSize: 11,
                                        fontWeight: 700,
                                        color: "#374151",
                                        textTransform: "uppercase",
                                        letterSpacing: ".05em",
                                      }}
                                    >
                                      Supporting Source Chunks
                                    </span>
                                    {item.supporting_sources.length === 0 && (
                                      <div
                                        style={{
                                          padding: "10px 12px",
                                          borderRadius: 10,
                                          background: "rgba(0,0,0,.03)",
                                          border: "1px solid rgba(0,0,0,.05)",
                                          fontSize: 11,
                                          color: "#6b7280",
                                        }}
                                      >
                                        No supporting source chunks were saved
                                        for this requirement.
                                      </div>
                                    )}
                                    {item.supporting_sources.map((source) => (
                                      <div
                                        key={source.source_id}
                                        style={{
                                          display: "grid",
                                          gap: 10,
                                          padding: "12px",
                                          borderRadius: 12,
                                          border: "1px solid rgba(0,0,0,.06)",
                                          background: "rgba(255,255,255,.78)",
                                        }}
                                      >
                                        <div
                                          style={{
                                            display: "flex",
                                            alignItems: "center",
                                            justifyContent: "space-between",
                                            gap: 10,
                                            flexWrap: "wrap" as const,
                                          }}
                                        >
                                          <span
                                            style={{
                                              fontSize: 12,
                                              fontWeight: 700,
                                              color: "#1f2937",
                                            }}
                                          >
                                            {source.source_id}
                                          </span>
                                          <div
                                            style={{
                                              display: "flex",
                                              gap: 10,
                                              flexWrap: "wrap" as const,
                                              fontSize: 10,
                                              color: "#6b7280",
                                            }}
                                          >
                                            <span>
                                              rank{" "}
                                              {source.retrieval_rank || "—"}
                                            </span>
                                            <span>
                                              rerank{" "}
                                              {source.rerank_score || "—"}
                                            </span>
                                          </div>
                                        </div>

                                        <ExpandableTraceText
                                          text={source.source_chunk_text}
                                          maxChars={320}
                                          emptyLabel="Source chunk text missing."
                                        />
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div
              style={{
                border: `1px solid ${assertionJob?.error ? "rgba(248,113,113,.25)" : assertionSaved.exists ? "rgba(16,185,129,.25)" : "rgba(245,158,11,.25)"}`,
                borderRadius: 16,
                background: "rgba(245,158,11,.04)",
                overflow: "hidden",
                opacity:
                  !traceabilityReady && !assertionJob?.running ? 0.78 : 1,
              }}
            >
              <div
                style={{
                  padding: "14px 20px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  borderBottom: "1px solid rgba(0,0,0,.05)",
                  gap: 12,
                  flexWrap: "wrap" as const,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: 10,
                      flexShrink: 0,
                      background: "rgba(245,158,11,.12)",
                      border: "1px solid rgba(245,158,11,.2)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <ShieldAlert size={16} style={{ color: "#d97706" }} />
                  </div>
                  <div>
                    <p
                      style={{
                        fontSize: 13,
                        fontWeight: 700,
                        color: "#57606a",
                        lineHeight: 1.3,
                      }}
                    >
                      Assertion Mapping
                    </p>
                    <p style={{ fontSize: 11, color: "#57606a", marginTop: 1 }}>
                      {assertionJob?.running
                        ? `Processing ${assertionJob.progress} / ${assertionJob.total} requirements…`
                        : assertionSaved.exists
                          ? `Saved ${assertionSaved.total_rows} assertion rows from traceability`
                          : traceabilityReady
                            ? "Runs from the saved traceability report"
                            : "Generate traceability first to enable assertion"}
                    </p>
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    flexShrink: 0,
                    flexWrap: "wrap" as const,
                  }}
                >
                  {assertionJob?.running && (
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 7,
                        padding: "8px 14px",
                        borderRadius: 10,
                        border: "1px solid rgba(245,158,11,.18)",
                        background: "rgba(245,158,11,.08)",
                        fontSize: 12,
                        fontWeight: 700,
                        color: "#b45309",
                      }}
                    >
                      <Loader2
                        size={13}
                        style={{ animation: "spin 1s linear infinite" }}
                      />
                      Running
                    </div>
                  )}
                  {!assertionJob?.running && !assertionSaved.exists && (
                    <button
                      onClick={startAssertion}
                      disabled={!traceabilityReady}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 7,
                        padding: "8px 18px",
                        borderRadius: 10,
                        border: "none",
                        cursor: traceabilityReady ? "pointer" : "not-allowed",
                        fontSize: 12,
                        fontWeight: 700,
                        color: "#fff",
                        opacity: traceabilityReady ? 1 : 0.5,
                        background: "linear-gradient(135deg,#f59e0b,#f97316)",
                        boxShadow: "0 0 18px rgba(245,158,11,.25)",
                      }}
                    >
                      <Zap size={13} /> Run Assertion
                    </button>
                  )}
                  {!assertionJob?.running && assertionSaved.exists && (
                    <>
                      <button
                        onClick={() => setConfirmAction("rerun-assertion")}
                        title="Re-run assertion analysis"
                        aria-label="Re-run assertion analysis"
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "8px 14px",
                          borderRadius: 10,
                          border: "1px solid rgba(0,0,0,.08)",
                          background: "transparent",
                          cursor: "pointer",
                          fontSize: 12,
                          fontWeight: 600,
                          color: "#57606a",
                        }}
                      >
                        <RefreshCw size={12} />
                      </button>
                      <button
                        onClick={() => setConfirmAction("clear-assertion")}
                        title="Clear assertion report"
                        aria-label="Clear assertion report"
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "8px 14px",
                          borderRadius: 10,
                          border: "1px solid rgba(239,68,68,.25)",
                          background: "rgba(248,113,113,.06)",
                          cursor: "pointer",
                          fontSize: 12,
                          fontWeight: 700,
                          color: "#dc2626",
                        }}
                      >
                        <Eraser size={12} />
                      </button>
                      <button
                        onClick={downloadAssertionCsv}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 7,
                          padding: "8px 18px",
                          borderRadius: 10,
                          border: "1px solid rgba(245,158,11,.3)",
                          cursor: "pointer",
                          fontSize: 12,
                          fontWeight: 700,
                          color: "#b45309",
                          background: "rgba(245,158,11,.08)",
                        }}
                      >
                        <Download size={13} />
                      </button>
                      <button
                        onClick={downloadAssertionFile}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 7,
                          padding: "8px 18px",
                          borderRadius: 10,
                          border: "none",
                          cursor: "pointer",
                          fontSize: 12,
                          fontWeight: 700,
                          color: "#fff",
                          background: "linear-gradient(135deg,#f59e0b,#f97316)",
                          boxShadow: "0 0 16px rgba(245,158,11,.3)",
                        }}
                      >
                        <Braces size={13} />
                      </button>
                    </>
                  )}
                </div>
              </div>

              {assertionJob?.running && (
                <div
                  style={{
                    padding: "10px 20px",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    borderBottom: "1px solid rgba(0,0,0,.04)",
                    background: "rgba(245,158,11,.04)",
                  }}
                >
                  <Loader2
                    size={13}
                    style={{
                      color: "#d97706",
                      animation: "spin 1s linear infinite",
                    }}
                  />
                  <span
                    style={{ fontSize: 12, color: "#374151", fontWeight: 600 }}
                  >
                    {assertionJob.current ?? "Preparing assertion run…"}
                  </span>
                </div>
              )}

              {/* {(assertionJob?.running || assertionSaved.exists) && (
                <div
                  style={{
                    padding: "12px 20px",
                    display: "flex",
                    gap: 10,
                    flexWrap: "wrap" as const,
                    borderBottom: "1px solid rgba(0,0,0,.04)",
                  }}
                >
                  {[
                    { label: "Rows", value: assertionSaved.total_rows },
                    { label: "Accepted", value: assertionSaved.accepted },
                    { label: "Weak", value: assertionSaved.weak },
                    { label: "Rejected", value: assertionSaved.rejected },
                  ].map((item) => (
                    <div
                      key={item.label}
                      style={{
                        padding: "8px 10px",
                        borderRadius: 10,
                        background: "rgba(255,255,255,.75)",
                        border: "1px solid rgba(0,0,0,.05)",
                        minWidth: 92,
                      }}
                    >
                      <p
                        style={{
                          fontSize: 10,
                          textTransform: "uppercase" as const,
                          letterSpacing: ".06em",
                          color: "#57606a",
                        }}
                      >
                        {item.label}
                      </p>
                      <p
                        style={{
                          fontSize: 16,
                          fontWeight: 700,
                          color: "#1f2937",
                        }}
                      >
                        {item.value}
                      </p>
                    </div>
                  ))}
                </div>
              )} */}

              {assertionJob &&
                (assertionJob.running || assertionSaved.exists) &&
                assertionJob.total > 0 && (
                  <div
                    style={{
                      padding: "10px 20px 0",
                      borderBottom: "1px solid rgba(0,0,0,.04)",
                    }}
                  >
                    <div
                      style={{
                        height: 3,
                        borderRadius: 3,
                        background: "rgba(0,0,0,.06)",
                        overflow: "hidden",
                        marginBottom: 8,
                      }}
                    >
                      <div
                        style={{
                          height: "100%",
                          borderRadius: 3,
                          background: assertionJob.error
                            ? "#dc2626"
                            : assertionSaved.exists && !assertionJob.running
                              ? "linear-gradient(90deg,#10b981,#34d399)"
                              : "linear-gradient(90deg,#f59e0b,#f97316)",
                          width: `${Math.round((assertionJob.progress / Math.max(assertionJob.total, 1)) * 100)}%`,
                          transition: "width .5s ease",
                        }}
                      />
                    </div>
                  </div>
                )}

              {assertionJob &&
                (assertionJob.running ||
                  assertionJob.logs.length > 0 ||
                  assertionSaved.exists ||
                  !!assertionJob.error) && (
                  <div
                    ref={assertionLogBoxRef}
                    style={{
                      maxHeight: 220,
                      overflowY: "auto",
                      padding: "10px 16px",
                      background: "rgba(0,0,0,.04)",
                      fontFamily: "monospace",
                      fontSize: 11,
                      lineHeight: 1.7,
                      borderTop: "1px solid rgba(0,0,0,.04)",
                    }}
                  >
                    {assertionJob.logs.length === 0 && assertionJob.running && (
                      <div
                        style={{
                          color: "#57606a",
                          whiteSpace: "pre-wrap" as const,
                        }}
                      >
                        Waiting for first assertion log...
                      </div>
                    )}
                    {assertionJob.logs.map((line, i) => {
                      const isError = line.startsWith("✗");
                      const isDone = line.startsWith("✓");
                      const isSep = line.startsWith("─");
                      const isLlmErr = line.includes("LLM ✗");
                      const isLlmOut = line.includes("LLM →");
                      const isLlmIn = line.includes("LLM ←");
                      const isAssertion = line.includes("Assertion");
                      const color =
                        isError || isLlmErr
                          ? "#dc2626"
                          : isDone
                            ? "#059669"
                            : isSep
                              ? "#1f2328"
                              : isLlmOut
                                ? "#0f766e"
                                : isLlmIn
                                  ? "#0369a1"
                                  : isAssertion
                                    ? "#d97706"
                                    : "#57606a";
                      return (
                        <div
                          key={i}
                          style={{ color, whiteSpace: "pre-wrap" as const }}
                        >
                          {line}
                        </div>
                      );
                    })}
                    {assertionJob.running && (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          color: "#d97706",
                          marginTop: 4,
                        }}
                      >
                        <Loader2
                          size={10}
                          style={{ animation: "spin 1s linear infinite" }}
                        />
                        <span>{assertionJob.current ?? "Processing…"}</span>
                      </div>
                    )}
                  </div>
                )}

              {assertionJob?.error && (
                <div
                  style={{
                    padding: "10px 20px",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    background: "rgba(248,113,113,.07)",
                    borderTop: "1px solid rgba(248,113,113,.15)",
                  }}
                >
                  <AlertCircle
                    size={13}
                    style={{ color: "#dc2626", flexShrink: 0 }}
                  />
                  <span style={{ fontSize: 12, color: "#ef4444" }}>
                    {assertionJob.error}
                  </span>
                </div>
              )}

              {/* {!assertionJob?.running && (
                <div
                  style={{
                    padding: "8px 20px",
                    borderTop: "1px solid rgba(0,0,0,.04)",
                    display: "flex",
                    gap: 20,
                    flexWrap: "wrap" as const,
                  }}
                >
                  {[
                    {
                      label: "Dependency",
                      value: traceabilityReady
                        ? "Saved traceability report"
                        : "Traceability required",
                    },
                    {
                      label: "Freshness",
                      value: assertionSaved.exists
                        ? assertionSaved.fresh
                          ? "Matches traceability"
                          : "Needs re-run"
                        : "Not generated",
                    },
                    { label: "Rows", value: "All verified test evidence rows" },
                  ].map((item) => (
                    <div
                      key={item.label}
                      style={{
                        display: "flex",
                        flexDirection: "column" as const,
                        gap: 1,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 9,
                          color: "#374151",
                          textTransform: "uppercase" as const,
                          letterSpacing: ".06em",
                        }}
                      >
                        {item.label}
                      </span>
                      <span
                        style={{
                          fontSize: 11,
                          color: "#b45309",
                          fontWeight: 600,
                        }}
                      >
                        {item.value}
                      </span>
                    </div>
                  ))}
                </div>
              )} */}
            </div>

            <div
              style={{
                border: `1px solid ${generatedTestsJob?.error ? "rgba(248,113,113,.25)" : generatedTestsSaved.exists ? "rgba(16,185,129,.25)" : "rgba(14,165,233,.25)"}`,
                borderRadius: 16,
                background: "rgba(14,165,233,.04)",
                overflow: "hidden",
                opacity:
                  !assertionReadyForTests && !generatedTestsJob?.running
                    ? 0.78
                    : 1,
              }}
            >
              <div
                style={{
                  padding: "14px 20px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  borderBottom: "1px solid rgba(0,0,0,.05)",
                  gap: 12,
                  flexWrap: "wrap" as const,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: 10,
                      flexShrink: 0,
                      background: "rgba(14,165,233,.12)",
                      border: "1px solid rgba(14,165,233,.2)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <Sparkles size={16} style={{ color: "#0284c7" }} />
                  </div>
                  <div>
                    <p
                      style={{
                        fontSize: 13,
                        fontWeight: 700,
                        color: "#57606a",
                        lineHeight: 1.3,
                      }}
                    >
                      Generated Tests
                    </p>
                    <p style={{ fontSize: 11, color: "#57606a", marginTop: 1 }}>
                      {generatedTestsJob?.running
                        ? `Generating ${generatedTestsJob.progress} / ${generatedTestsJob.total} framework files…`
                        : generatedTestsSaved.exists
                          ? `Saved ${generatedTestsSaved.total_files} files for ${generatedTestsSaved.total_gap_groups} gap groups`
                          : assertionReadyForTests
                            ? "Runs from the saved assertion report"
                            : "Run assertion first to enable generated tests"}
                    </p>
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    flexShrink: 0,
                    flexWrap: "wrap" as const,
                  }}
                >
                  {generatedTestsJob?.running && (
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 7,
                        padding: "8px 14px",
                        borderRadius: 10,
                        border: "1px solid rgba(14,165,233,.18)",
                        background: "rgba(14,165,233,.08)",
                        fontSize: 12,
                        fontWeight: 700,
                        color: "#0369a1",
                      }}
                    >
                      <Loader2
                        size={13}
                        style={{ animation: "spin 1s linear infinite" }}
                      />
                      Running
                    </div>
                  )}
                  {!generatedTestsJob?.running &&
                    !generatedTestsSaved.exists && (
                      <button
                        onClick={startGeneratedTests}
                        disabled={!assertionReadyForTests}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 7,
                          padding: "8px 18px",
                          borderRadius: 10,
                          border: "none",
                          cursor: assertionReadyForTests
                            ? "pointer"
                            : "not-allowed",
                          fontSize: 12,
                          fontWeight: 700,
                          color: "#fff",
                          opacity: assertionReadyForTests ? 1 : 0.5,
                          background: "linear-gradient(135deg,#0ea5e9,#06b6d4)",
                          boxShadow: "0 0 18px rgba(14,165,233,.25)",
                        }}
                      >
                        <Sparkles size={13} /> Generate Tests
                      </button>
                    )}
                  {!generatedTestsJob?.running &&
                    generatedTestsSaved.exists && (
                      <>
                        <button
                          onClick={() =>
                            setConfirmAction("rerun-generated-tests")
                          }
                          title="Re-run generated tests"
                          aria-label="Re-run generated tests"
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            padding: "8px 14px",
                            borderRadius: 10,
                            border: "1px solid rgba(0,0,0,.08)",
                            background: "transparent",
                            cursor: "pointer",
                            fontSize: 12,
                            fontWeight: 600,
                            color: "#57606a",
                          }}
                        >
                          <RefreshCw size={12} />
                        </button>
                        <button
                          onClick={() =>
                            setConfirmAction("clear-generated-tests")
                          }
                          title="Clear generated tests"
                          aria-label="Clear generated tests"
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            padding: "8px 14px",
                            borderRadius: 10,
                            border: "1px solid rgba(239,68,68,.25)",
                            background: "rgba(248,113,113,.06)",
                            cursor: "pointer",
                            fontSize: 12,
                            fontWeight: 700,
                            color: "#dc2626",
                          }}
                        >
                          <Eraser size={12} />
                        </button>
                        <button
                          onClick={downloadGeneratedTestsManifest}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 7,
                            padding: "8px 18px",
                            borderRadius: 10,
                            border: "1px solid rgba(14,165,233,.25)",
                            cursor: "pointer",
                            fontSize: 12,
                            fontWeight: 700,
                            color: "#0369a1",
                            background: "rgba(14,165,233,.08)",
                          }}
                        >
                          <FileJson size={13} />
                        </button>
                      </>
                    )}
                </div>
              </div>

              {generatedTestsJob?.running && (
                <div
                  style={{
                    padding: "10px 20px",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    borderBottom: "1px solid rgba(0,0,0,.04)",
                    background: "rgba(14,165,233,.04)",
                  }}
                >
                  <Loader2
                    size={13}
                    style={{
                      color: "#0284c7",
                      animation: "spin 1s linear infinite",
                    }}
                  />
                  <span
                    style={{ fontSize: 12, color: "#374151", fontWeight: 600 }}
                  >
                    {generatedTestsJob.current ?? "Preparing generated tests…"}
                  </span>
                </div>
              )}

              {/* {(generatedTestsJob?.running || generatedTestsSaved.exists) && (
                <div
                  style={{
                    padding: "12px 20px",
                    display: "flex",
                    gap: 10,
                    flexWrap: "wrap" as const,
                    borderBottom: "1px solid rgba(0,0,0,.04)",
                  }}
                >
                  {[
                    { label: "Files", value: generatedTestsSaved.total_files },
                    {
                      label: "Gap Groups",
                      value: generatedTestsSaved.total_gap_groups,
                    },
                    {
                      label: "Requirements",
                      value: generatedTestsSaved.total_gap_requirements,
                    },
                    {
                      label: "Warnings",
                      value: generatedTestsSaved.warnings.length,
                    },
                  ].map((item) => (
                    <div
                      key={item.label}
                      style={{
                        padding: "8px 10px",
                        borderRadius: 10,
                        background: "rgba(255,255,255,.75)",
                        border: "1px solid rgba(0,0,0,.05)",
                        minWidth: 92,
                      }}
                    >
                      <p
                        style={{
                          fontSize: 10,
                          textTransform: "uppercase" as const,
                          letterSpacing: ".06em",
                          color: "#57606a",
                        }}
                      >
                        {item.label}
                      </p>
                      <p
                        style={{
                          fontSize: 16,
                          fontWeight: 700,
                          color: "#1f2937",
                        }}
                      >
                        {item.value}
                      </p>
                    </div>
                  ))}
                </div>
              )} */}

              {generatedTestsJob &&
                (generatedTestsJob.running || generatedTestsSaved.exists) &&
                generatedTestsJob.total > 0 && (
                  <div
                    style={{
                      padding: "10px 20px 0",
                      borderBottom: "1px solid rgba(0,0,0,.04)",
                    }}
                  >
                    <div
                      style={{
                        height: 3,
                        borderRadius: 3,
                        background: "rgba(0,0,0,.06)",
                        overflow: "hidden",
                        marginBottom: 8,
                      }}
                    >
                      <div
                        style={{
                          height: "100%",
                          borderRadius: 3,
                          background: generatedTestsJob.error
                            ? "#dc2626"
                            : generatedTestsSaved.exists &&
                                !generatedTestsJob.running
                              ? "linear-gradient(90deg,#10b981,#34d399)"
                              : "linear-gradient(90deg,#0ea5e9,#06b6d4)",
                          width: `${Math.round((generatedTestsJob.progress / Math.max(generatedTestsJob.total, 1)) * 100)}%`,
                          transition: "width .5s ease",
                        }}
                      />
                    </div>
                  </div>
                )}

              {generatedTestsJob &&
                (generatedTestsJob.running ||
                  generatedTestsJob.logs.length > 0 ||
                  generatedTestsSaved.exists ||
                  !!generatedTestsJob.error) && (
                  <div
                    ref={generatedTestsLogBoxRef}
                    style={{
                      maxHeight: 220,
                      overflowY: "auto",
                      padding: "10px 16px",
                      background: "rgba(0,0,0,.04)",
                      fontFamily: "monospace",
                      fontSize: 11,
                      lineHeight: 1.7,
                      borderTop: "1px solid rgba(0,0,0,.04)",
                    }}
                  >
                    {generatedTestsJob.logs.length === 0 &&
                      generatedTestsJob.running && (
                        <div
                          style={{
                            color: "#57606a",
                            whiteSpace: "pre-wrap" as const,
                          }}
                        >
                          Waiting for first generated-test log...
                        </div>
                      )}
                    {generatedTestsJob.logs.map((line, i) => {
                      const isError = line.startsWith("✗");
                      const isDone = line.startsWith("✓");
                      const isSep = line.startsWith("─");
                      const isLlmErr = line.includes("LLM ✗");
                      const isLlmOut = line.includes("LLM →");
                      const isLlmIn = line.includes("LLM ←");
                      const isCluster = line.includes("Cluster");
                      const isGenerate = line.includes("Generate");
                      const isWarning =
                        line.includes("skipped=") || line.includes("warning");
                      const color =
                        isError || isLlmErr
                          ? "#dc2626"
                          : isDone
                            ? "#059669"
                            : isSep
                              ? "#1f2328"
                              : isLlmOut
                                ? "#0f766e"
                                : isLlmIn
                                  ? "#0369a1"
                                  : isWarning
                                    ? "#d97706"
                                    : isGenerate
                                      ? "#7c3aed"
                                      : isCluster
                                        ? "#0284c7"
                                        : "#57606a";
                      return (
                        <div
                          key={i}
                          style={{ color, whiteSpace: "pre-wrap" as const }}
                        >
                          {line}
                        </div>
                      );
                    })}
                    {generatedTestsJob.running && (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          color: "#0284c7",
                          marginTop: 4,
                        }}
                      >
                        <Loader2
                          size={10}
                          style={{ animation: "spin 1s linear infinite" }}
                        />
                        <span>
                          {generatedTestsJob.current ?? "Processing…"}
                        </span>
                      </div>
                    )}
                  </div>
                )}

              {generatedTestsSaved.exists &&
                generatedTestsSaved.files.length > 0 &&
                !generatedTestsJob?.running && (
                  <div
                    style={{
                      padding: "12px 20px",
                      borderTop: "1px solid rgba(0,0,0,.04)",
                      display: "flex",
                      gap: 8,
                      flexWrap: "wrap" as const,
                    }}
                  >
                    {generatedTestsSaved.files.map((file) => (
                      <button
                        key={file.filename}
                        onClick={() => downloadGeneratedTestFile(file.filename)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 7,
                          padding: "8px 14px",
                          borderRadius: 10,
                          border: "1px solid rgba(14,165,233,.2)",
                          cursor: "pointer",
                          fontSize: 12,
                          fontWeight: 700,
                          color: "#0369a1",
                          background: "rgba(14,165,233,.08)",
                        }}
                        title={`${file.framework} • ${file.language}`}
                      >
                        <Download size={13} /> {file.filename}
                      </button>
                    ))}
                  </div>
                )}

              {generatedTestsSaved.exists &&
                generatedTestsSaved.warnings.length > 0 && (
                  <div
                    style={{
                      padding: "10px 20px",
                      borderTop: "1px solid rgba(0,0,0,.04)",
                      background: "rgba(245,158,11,.06)",
                    }}
                  >
                    <p
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        color: "#b45309",
                        marginBottom: 6,
                      }}
                    >
                      Warnings
                    </p>
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column" as const,
                        gap: 4,
                      }}
                    >
                      {generatedTestsSaved.warnings.map((warning, idx) => (
                        <div
                          key={`${warning}_${idx}`}
                          style={{ fontSize: 11, color: "#b45309" }}
                        >
                          {warning}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {generatedTestsJob?.error && (
                <div
                  style={{
                    padding: "10px 20px",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    background: "rgba(248,113,113,.07)",
                    borderTop: "1px solid rgba(248,113,113,.15)",
                  }}
                >
                  <AlertCircle
                    size={13}
                    style={{ color: "#dc2626", flexShrink: 0 }}
                  />
                  <span style={{ fontSize: 12, color: "#ef4444" }}>
                    {generatedTestsJob.error}
                  </span>
                </div>
              )}

              {/* {!generatedTestsJob?.running && (
                <div
                  style={{
                    padding: "8px 20px",
                    borderTop: "1px solid rgba(0,0,0,.04)",
                    display: "flex",
                    gap: 20,
                    flexWrap: "wrap" as const,
                  }}
                >
                  {[
                    {
                      label: "Dependency",
                      value: assertionReadyForTests
                        ? "Saved assertion report"
                        : "Assertion required",
                    },
                    {
                      label: "Freshness",
                      value: generatedTestsSaved.exists
                        ? generatedTestsSaved.fresh
                          ? "Matches assertion"
                          : "Needs re-run"
                        : "Not generated",
                    },
                    {
                      label: "Output",
                      value: "Manifest + framework files",
                    },
                  ].map((item) => (
                    <div
                      key={item.label}
                      style={{
                        display: "flex",
                        flexDirection: "column" as const,
                        gap: 1,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 9,
                          color: "#374151",
                          textTransform: "uppercase" as const,
                          letterSpacing: ".06em",
                        }}
                      >
                        {item.label}
                      </span>
                      <span
                        style={{
                          fontSize: 11,
                          color: "#0369a1",
                          fontWeight: 600,
                        }}
                      >
                        {item.value}
                      </span>
                    </div>
                  ))}
                </div>
              )} */}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function FileUploader() {
  const [files, setFiles] = useState<FileStore>({
    requirement: [],
    test: [],
    source: [],
  });
  const [active, setActive] = useState<SectionKey>("requirement");
  const [loading, setLoading] = useState(true);
  const [online, setOnline] = useState(true);
  const [view, setView] = useState<"upload" | "embed">("upload");
  const [theme, setTheme] = useState<ThemeMode>(() => {
    if (typeof window === "undefined") return "light";
    const stored = window.localStorage.getItem("fu_theme_mode");
    if (stored === "light" || stored === "dark") return stored;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });
  const [rechunking, setRechunking] = useState(false);
  const [confirmRechunk, setConfirmRechunk] = useState(false);
  const [rechunkMsg, setRechunkMsg] = useState<{
    ok: boolean;
    text: string;
  } | null>(null);

  // ── Project state (persisted in localStorage) ─────────────────────────────
  const [projects, setProjects] = useState<
    { id: string; name: string; createdAt: number }[]
  >(() => {
    try {
      return JSON.parse(localStorage.getItem("fu_projects") ?? "[]");
    } catch {
      return [];
    }
  });
  const [activeProjectId, setActiveProjectId] = useState<string | null>(
    () => localStorage.getItem("fu_active_project") ?? null,
  );
  const [newProjectName, setNewProjectName] = useState("");

  // Persist project list and active id on change
  useEffect(() => {
    localStorage.setItem("fu_projects", JSON.stringify(projects));
  }, [projects]);
  useEffect(() => {
    if (activeProjectId)
      localStorage.setItem("fu_active_project", activeProjectId);
    else localStorage.removeItem("fu_active_project");
  }, [activeProjectId]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.style.colorScheme = theme;
    window.localStorage.setItem("fu_theme_mode", theme);
  }, [theme]);

  const activeProject = projects.find((p) => p.id === activeProjectId) ?? null;

  // Create a new project and make it active
  const handleCreateProject = () => {
    const name = newProjectName.trim();
    if (!name) return;
    const p = {
      id: `${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
      name,
      createdAt: Date.now(),
    };
    setProjects((prev) => [p, ...prev]);
    setActiveProjectId(p.id);
    setNewProjectName("");
  };

  // Restore from backend
  useEffect(() => {
    fetch(`${API}/api/files`)
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((data: UploadedFile[]) => {
        setOnline(true);
        const store: FileStore = { requirement: [], test: [], source: [] };
        data.forEach((f) => {
          if (f.category in store) store[f.category].push(f);
        });
        setFiles(store);
      })
      .catch(() => setOnline(false))
      .finally(() => setLoading(false));
  }, []);

  const uploadFile = useCallback(async (key: SectionKey, file: File) => {
    const id = tmpId();
    const placeholder: UploadedFile = {
      id,
      name: file.name,
      category: key,
      size_bytes: file.size,
      uploaded_at: new Date().toISOString(),
      chunk_count: 0,
      chunk_size: 0,
      chunk_overlap: 0,
      uploading: true,
    };
    setFiles((prev) => ({ ...prev, [key]: [...prev[key], placeholder] }));
    try {
      const form = new FormData();
      form.append("category", key);
      form.append("file", file, file.name);
      const res = await fetch(`${API}/api/files/upload`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error();
      const saved: UploadedFile = await res.json();
      setFiles((prev) => ({
        ...prev,
        [key]: prev[key].map((f) => (f.id === id ? saved : f)),
      }));
      setOnline(true);
    } catch {
      setFiles((prev) => ({
        ...prev,
        [key]: prev[key].map((f) =>
          f.id === id ? { ...f, uploading: false, error: "failed" } : f,
        ),
      }));
    }
  }, []);

  const addFiles = useCallback(
    (key: SectionKey, incoming: File[]) => {
      const existing = new Set(files[key].map((f) => f.name));
      incoming
        .filter((f) => !existing.has(f.name))
        .forEach((f) => uploadFile(key, f));
    },
    [files, uploadFile],
  );

  const removeFile = useCallback(
    async (key: SectionKey, id: string) => {
      const file = files[key].find((f) => f.id === id);
      if (!file || file.uploading) return;
      setFiles((prev) => ({
        ...prev,
        [key]: prev[key].filter((f) => f.id !== id),
      }));
      if (!file.error)
        fetch(`${API}/api/files/${id}`, { method: "DELETE" }).catch(() => {});
    },
    [files],
  );

  const clearSection = useCallback(
    async (key: SectionKey) => {
      const ids = files[key]
        .filter((f) => !f.uploading && !f.error)
        .map((f) => f.id);
      setFiles((prev) => ({ ...prev, [key]: [] }));
      await Promise.allSettled(
        ids.map((id) => fetch(`${API}/api/files/${id}`, { method: "DELETE" })),
      );
    },
    [files],
  );

  const rechunkAll = useCallback(async () => {
    setRechunking(true);
    setRechunkMsg(null);
    try {
      const res = await fetch(`${API}/api/files/rechunk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (!res.ok) {
        setRechunkMsg({ ok: false, text: data.detail ?? "Rechunk failed" });
        return;
      }
      // Refresh file list so chunk_count badges update
      const r2 = await fetch(`${API}/api/files`);
      if (r2.ok) {
        const updated: UploadedFile[] = await r2.json();
        const store: FileStore = { requirement: [], test: [], source: [] };
        updated.forEach((f) => {
          if (f.category in store) store[f.category as SectionKey].push(f);
        });
        setFiles(store);
      }
      const errs = (data.errors ?? []).length;
      setRechunkMsg({
        ok: errs === 0,
        text:
          errs === 0
            ? `Rechunked ${data.rechunked} file${data.rechunked !== 1 ? "s" : ""} successfully`
            : `Rechunked ${data.rechunked} files · ${errs} error${errs !== 1 ? "s" : ""}`,
      });
      setTimeout(() => setRechunkMsg(null), 4000);
    } catch {
      setRechunkMsg({ ok: false, text: "Network error — backend unreachable" });
    } finally {
      setRechunking(false);
    }
  }, []);

  const handleConfirmRechunk = () => {
    setConfirmRechunk(false);
    void rechunkAll();
  };

  const allFiles = Object.values(files).flat();
  const totalFiles = allFiles.filter((f) => !f.error).length;
  const totalChunks = allFiles
    .filter((f) => !f.uploading && !f.error)
    .reduce((s, f) => s + f.chunk_count, 0);
  const anyUploading = allFiles.some((f) => f.uploading);
  const activeSection = SECTIONS.find((s) => s.key === active)!;
  const activeFiles = files[active];
  const sectionUploading = activeFiles.some((f) => f.uploading);

  // ── Loading ─────────────────────────────────────────────────────────────────
  if (loading)
    return (
      <div
        style={{
          height: "100vh",
          background: "#f6f8fa",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 16,
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 14,
            background: "rgba(99,102,241,.15)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          className="float"
        >
          <Layers size={22} style={{ color: "#4f46e5" }} />
        </div>
        <p style={{ fontSize: 13, color: "#57606a", letterSpacing: ".04em" }}>
          Initialising workspace…
        </p>
      </div>
    );

  // ── UI ──────────────────────────────────────────────────────────────────────
  return (
    <div
      className="fu-theme-scope"
      style={{
        height: "100vh",
        background: "#f6f8fa",
        display: "flex",
        overflow: "hidden",
        position: "relative",
      }}
    >
      <GridBg />

      <ActionConfirmDialog
        open={confirmRechunk}
        title="Re-chunk uploaded files"
        subtitle="Rebuilds chunk boundaries with the current splitter settings"
        description={`This will process all ${totalFiles} uploaded file${totalFiles === 1 ? "" : "s"} again and replace their saved chunk boundaries and chunk counts. It does not delete the files themselves.`}
        note="If the chunk layout changes, re-run embedding and downstream analysis so the index and reports stay in sync."
        confirmLabel="Proceed and rechunk"
        tone="warning"
        Icon={RefreshCw}
        onConfirm={handleConfirmRechunk}
        onCancel={() => setConfirmRechunk(false)}
      />

      {/* ══════════ SIDEBAR ══════════ */}
      <aside
        style={{
          width: 260,
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          borderRight: "1px solid rgba(0,0,0,.06)",
          background: "rgba(255,255,255,.9)",
          backdropFilter: "blur(12px)",
          position: "relative",
          zIndex: 10,
        }}
      >
        {/* Brand */}
        <div
          style={{
            padding: "20px 16px 18px",
            borderBottom: "1px solid rgba(0,0,0,.05)",
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 12,
              flexShrink: 0,
              background:
                "linear-gradient(135deg,rgba(99,102,241,.3),rgba(139,92,246,.3))",
              border: "1px solid rgba(99,102,241,.3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 20px rgba(99,102,241,.2)",
            }}
          >
            <Layers size={16} style={{ color: "#6366f1" }} />
          </div>
          <div>
            <p
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: "#1f2328",
                lineHeight: 1.2,
              }}
            >
              Lantern
            </p>
            <p
              style={{
                fontSize: 10,
                color: "#57606a",
                marginTop: 1,
                letterSpacing: ".04em",
              }}
            >
              Semantic Gap Analysis Tool
            </p>
          </div>
        </div>

        {/* ── Projects panel ── */}

        {/* Nav label */}
        <div style={{ padding: "14px 16px 10px" }}>
          <p
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: "#374151",
              textTransform: "uppercase",
              letterSpacing: ".1em",
            }}
          >
            Artefacts
          </p>
        </div>

        {/* Tabs */}
        <nav
          style={{
            padding: "0 8px",
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}
        >
          {SECTIONS.map((s) => (
            <SidebarTab
              key={s.key}
              section={s}
              count={files[s.key].length}
              isActive={active === s.key}
              uploading={files[s.key].some((f) => f.uploading)}
              onClick={() => setActive(s.key)}
            />
          ))}
        </nav>

        {/* Divider */}
        <div style={{ flex: 1 }} />

        {/* Stats */}
        <div
          style={{
            margin: "12px 12px",
            background: "rgba(0,0,0,.03)",
            border: "1px solid rgba(0,0,0,.06)",
            borderRadius: 14,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-around",
            }}
          >
            <StatCard value={totalFiles} label="Files" color="#6366f1" />
            <div
              style={{
                width: 1,
                background: "rgba(0,0,0,.05)",
                alignSelf: "stretch",
              }}
            />
            <StatCard value={totalChunks} label="Chunks" color="#10b981" />
            <div
              style={{
                width: 1,
                background: "rgba(0,0,0,.05)",
                alignSelf: "stretch",
              }}
            />
            <StatCard
              value={SECTIONS.filter((s) => files[s.key].length > 0).length}
              label="Active"
              color="#d97706"
            />
          </div>
        </div>

        {/* Theme toggle */}
        <div style={{ padding: "0 12px 12px" }}>
          <button
            onClick={() =>
              setTheme((prev) => (prev === "light" ? "dark" : "light"))
            }
            style={{
              width: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              padding: "8px 12px",
              borderRadius: 10,
              border: "1px solid rgba(0,0,0,.08)",
              background: "rgba(0,0,0,.03)",
              color: "#57606a",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {theme === "dark" ? <Sun size={13} /> : <Moon size={13} />}
            {theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          </button>
        </div>

        {/* Connection */}
        <div style={{ padding: "0 12px 16px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 12px",
              borderRadius: 10,
              background: online
                ? "rgba(16,185,129,.08)"
                : "rgba(248,113,113,.08)",
              border: `1px solid ${online ? "rgba(16,185,129,.2)" : "rgba(248,113,113,.2)"}`,
            }}
          >
            <div
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: online ? "#059669" : "#dc2626",
                boxShadow: online ? "0 0 6px #34d399" : "0 0 6px #f87171",
                animation: "glow-pulse 2s ease infinite",
              }}
            />
            {online ? (
              <Wifi size={12} style={{ color: "#059669" }} />
            ) : (
              <WifiOff size={12} style={{ color: "#dc2626" }} />
            )}
            <span
              style={{
                fontSize: 12,
                fontWeight: 500,
                color: online ? "#10b981" : "#ef4444",
              }}
            >
              {online ? "Backend connected" : "Backend offline"}
            </span>
          </div>
        </div>
      </aside>

      {/* ══════════ MAIN ══════════ */}
      <main
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
          position: "relative",
          zIndex: 10,
        }}
      >
        {view === "embed" && <EmbedPanel onBack={() => setView("upload")} />}
        {view === "upload" && (
          <>
            {/* Top bar */}
            <header
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0 28px",
                height: 64,
                flexShrink: 0,
                borderBottom: "1px solid rgba(0,0,0,.06)",
                backdropFilter: "blur(12px)",
                background: "rgba(255,255,255,.85)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: 10,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: activeSection.iconBg,
                    boxShadow: `0 0 16px ${activeSection.glow}`,
                  }}
                >
                  <activeSection.Icon
                    size={16}
                    style={{ color: activeSection.iconColor }}
                  />
                </div>
                <div>
                  <h1
                    style={{
                      fontSize: 14,
                      fontWeight: 700,
                      color: "#1f2328",
                      lineHeight: 1.2,
                    }}
                  >
                    {activeSection.label}
                  </h1>
                  <p style={{ fontSize: 11, color: "#57606a", marginTop: 1 }}>
                    {activeSection.desc}
                  </p>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {sectionUploading && (
                  <span
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "5px 12px",
                      borderRadius: 20,
                      background: "rgba(99,102,241,.12)",
                      border: "1px solid rgba(99,102,241,.2)",
                      fontSize: 12,
                      color: "#4f46e5",
                    }}
                  >
                    <Loader2
                      size={11}
                      style={{ animation: "spin 1s linear infinite" }}
                    />
                    Processing…
                  </span>
                )}
                {!sectionUploading &&
                  activeFiles.length > 0 &&
                  !activeFiles.some((f) => f.error) && (
                    <span
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        padding: "5px 12px",
                        borderRadius: 20,
                        background: "rgba(16,185,129,.1)",
                        border: "1px solid rgba(16,185,129,.2)",
                        fontSize: 12,
                        color: "#059669",
                      }}
                    >
                      <CheckCircle2 size={11} />
                      {activeFiles.length} file
                      {activeFiles.length !== 1 ? "s" : ""} ready
                    </span>
                  )}
                {activeFiles.length > 0 && !sectionUploading && (
                  <button
                    onClick={() => clearSection(active)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "5px 12px",
                      borderRadius: 20,
                      background: "transparent",
                      border: "1px solid rgba(0,0,0,.06)",
                      fontSize: 12,
                      color: "#57606a",
                      cursor: "pointer",
                      transition: "all .15s",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background =
                        "rgba(248,113,113,.08)";
                      e.currentTarget.style.borderColor =
                        "rgba(248,113,113,.2)";
                      e.currentTarget.style.color = "#dc2626";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "transparent";
                      e.currentTarget.style.borderColor = "rgba(0,0,0,.06)";
                      e.currentTarget.style.color = "#57606a";
                    }}
                  >
                    <X size={11} /> Clear section
                  </button>
                )}
              </div>
            </header>

            {/* Scrollable content */}
            <div style={{ flex: 1, overflowY: "auto", padding: "28px" }}>
              {/* Drop zone */}
              <DropZone
                section={activeSection}
                onFiles={(f) => addFiles(active, f)}
              />

              {/* File list */}
              {activeFiles.length > 0 && (
                <div
                  style={{
                    marginTop: 20,
                    border: "1px solid rgba(0,0,0,.06)",
                    borderRadius: 16,
                    overflow: "hidden",
                    background: "rgba(0,0,0,.02)",
                  }}
                  className="fade-up"
                >
                  {/* List header */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "10px 16px",
                      borderBottom: "1px solid rgba(0,0,0,.05)",
                      background: "rgba(0,0,0,.02)",
                    }}
                  >
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 8 }}
                    >
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          color: "#374151",
                          textTransform: "uppercase",
                          letterSpacing: ".08em",
                        }}
                      >
                        Uploaded files
                      </span>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: 20,
                          background: activeSection.pill.bg,
                          color: activeSection.pill.color,
                        }}
                      >
                        {activeFiles.length}
                      </span>
                    </div>
                    {!sectionUploading && (
                      <span style={{ fontSize: 11, color: "#374151" }}>
                        {activeFiles
                          .filter((f) => !f.uploading && !f.error)
                          .reduce((s, f) => s + f.chunk_count, 0)}{" "}
                        total chunks
                      </span>
                    )}
                  </div>

                  {/* Rows */}
                  {activeFiles.map((f) => (
                    <FileRow
                      key={f.id}
                      file={f}
                      onRemove={() => removeFile(active, f.id)}
                    />
                  ))}
                </div>
              )}

              {/* Empty state */}
              {activeFiles.length === 0 && (
                <EmptyState section={activeSection} />
              )}
            </div>

            {/* Footer / action bar */}
            <footer
              style={{
                flexShrink: 0,
                borderTop: "1px solid rgba(0,0,0,.06)",
                padding: "14px 28px",
                backdropFilter: "blur(12px)",
                background: "rgba(0,0,0,.07)",
                display: "flex",
                alignItems: "center",
                gap: 16,
              }}
            >
              {/* Section progress indicators */}
              <div
                style={{
                  flex: 1,
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                }}
              >
                {SECTIONS.map((s) => {
                  const count = files[s.key].length;
                  const uploading = files[s.key].some((f) => f.uploading);
                  return (
                    <div
                      key={s.key}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        cursor: "pointer",
                      }}
                      onClick={() => setActive(s.key)}
                    >
                      <div
                        style={{
                          width: 7,
                          height: 7,
                          borderRadius: "50%",
                          background: uploading
                            ? "#4f46e5"
                            : count > 0
                              ? s.dot
                              : "rgba(0,0,0,.08)",
                          boxShadow:
                            count > 0 && !uploading
                              ? `0 0 6px ${s.dot}`
                              : "none",
                          animation: uploading
                            ? "glow-pulse 1s ease infinite"
                            : "none",
                          transition: "all .3s",
                        }}
                      />
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 500,
                          color: active === s.key ? "#57606a" : "#374151",
                          transition: "color .15s",
                        }}
                      >
                        {s.short}
                      </span>
                      {count > 0 && (
                        <span style={{ fontSize: 10, color: "#57606a" }}>
                          {count}
                        </span>
                      )}
                    </div>
                  );
                })}

                {totalFiles > 0 && (
                  <span
                    style={{ fontSize: 11, color: "#374151", marginLeft: 4 }}
                  >
                    {totalFiles} file{totalFiles !== 1 ? "s" : ""} ·{" "}
                    {totalChunks} chunks
                  </span>
                )}
              </div>

              {/* Rechunk toast */}
              {rechunkMsg && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 7,
                    padding: "6px 14px",
                    borderRadius: 20,
                    fontSize: 12,
                    fontWeight: 500,
                    background: rechunkMsg.ok
                      ? "rgba(16,185,129,.1)"
                      : "rgba(248,113,113,.1)",
                    border: `1px solid ${rechunkMsg.ok ? "rgba(16,185,129,.25)" : "rgba(248,113,113,.25)"}`,
                    color: rechunkMsg.ok ? "#10b981" : "#ef4444",
                    flexShrink: 0,
                  }}
                >
                  {rechunkMsg.ok ? (
                    <CheckCircle2 size={12} />
                  ) : (
                    <AlertCircle size={12} />
                  )}
                  {rechunkMsg.text}
                </div>
              )}

              {/* Rechunk button */}
              {totalFiles > 0 && !anyUploading && (
                <button
                  onClick={() => setConfirmRechunk(true)}
                  disabled={rechunking}
                  title="Re-chunk all uploaded files with the current splitter config"
                  aria-label="Re-chunk all uploaded files with the current splitter config"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "8px 16px",
                    borderRadius: 10,
                    border: "1px solid rgba(251,191,36,.2)",
                    background: "rgba(251,191,36,.07)",
                    cursor: rechunking ? "default" : "pointer",
                    fontSize: 12,
                    fontWeight: 600,
                    color: "#d97706",
                    flexShrink: 0,
                    transition: "all .15s",
                  }}
                  onMouseEnter={(e) => {
                    if (!rechunking) {
                      e.currentTarget.style.background = "rgba(251,191,36,.14)";
                      e.currentTarget.style.borderColor = "rgba(251,191,36,.4)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "rgba(251,191,36,.07)";
                    e.currentTarget.style.borderColor = "rgba(251,191,36,.2)";
                  }}
                >
                  {rechunking ? (
                    <>
                      <Loader2
                        size={12}
                        style={{ animation: "spin 1s linear infinite" }}
                      />{" "}
                      Rechunking…
                    </>
                  ) : (
                    <>
                      <RefreshCw size={12} />
                    </>
                  )}
                </button>
              )}

              {/* CTA */}
              <button
                disabled={totalFiles === 0 || anyUploading}
                onClick={() =>
                  totalFiles > 0 && !anyUploading && setView("embed")
                }
                style={
                  {
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "10px 22px",
                    borderRadius: 12,
                    border: "none",
                    cursor: "pointer",
                    fontSize: 13,
                    fontWeight: 700,
                    background:
                      totalFiles > 0 && !anyUploading
                        ? "linear-gradient(135deg,#4f46e5,#7c3aed)"
                        : "rgba(0,0,0,.05)",
                    color: totalFiles > 0 && !anyUploading ? "#fff" : "#374151",
                    boxShadow:
                      totalFiles > 0 && !anyUploading
                        ? "0 0 24px rgba(99,102,241,.3), inset 0 1px 0 rgba(0,0,0,.08)"
                        : "none",
                    transition: "all .2s",
                    letterSpacing: ".01em",
                  } as CSSProperties
                }
                onMouseEnter={(e) => {
                  if (totalFiles > 0 && !anyUploading) {
                    e.currentTarget.style.transform = "translateY(-1px)";
                    e.currentTarget.style.boxShadow =
                      "0 0 32px rgba(99,102,241,.45), inset 0 1px 0 rgba(0,0,0,.12)";
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "translateY(0)";
                  e.currentTarget.style.boxShadow =
                    totalFiles > 0 && !anyUploading
                      ? "0 0 24px rgba(99,102,241,.3), inset 0 1px 0 rgba(0,0,0,.08)"
                      : "none";
                }}
              >
                {anyUploading ? (
                  <>
                    <Loader2
                      size={14}
                      style={{ animation: "spin 1s linear infinite" }}
                    />{" "}
                    Processing…
                  </>
                ) : totalFiles > 0 ? (
                  <>
                    <Sparkles size={14} /> Run Analysis{" "}
                    <ChevronRight size={14} style={{ opacity: 0.7 }} />
                  </>
                ) : (
                  <>Upload files to begin</>
                )}
              </button>
            </footer>
          </>
        )}
      </main>
    </div>
  );
}
