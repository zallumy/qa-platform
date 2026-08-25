export type StampStatus = "pass" | "fail" | "review" | "pending";

const MAP: Record<StampStatus, { label: string; cls: string }> = {
  pass: { label: "PASS", cls: "border-emerald-700 text-emerald-700" },
  fail: { label: "FAIL", cls: "border-red-700 text-red-700" },
  review: { label: "REVIEW", cls: "border-amber-600 text-amber-600" },
  pending: { label: "PENDING", cls: "border-stone-400 text-stone-500" },
};

export default function StatusStamp({ status }: { status: StampStatus }) {
  const s = MAP[status];
  return (
    <span
      className={`inline-block border-2 rounded px-2 py-0.5 text-xs font-bold tracking-widest -rotate-3 ${s.cls}`}
      style={{ fontFamily: "monospace" }}
    >
      {s.label}
    </span>
  );
}
