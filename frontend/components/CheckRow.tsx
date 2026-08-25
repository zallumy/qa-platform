import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react";

export default function CheckRow({
  label,
  pass,
  detail,
}: {
  label: string;
  pass: boolean | null | undefined;
  detail: string;
}) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-stone-200 last:border-0">
      <span className="text-sm text-stone-700">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-xs font-mono text-stone-500">{detail}</span>
        {pass === true && <CheckCircle2 className="w-4 h-4 text-emerald-700" />}
        {pass === false && <XCircle className="w-4 h-4 text-red-700" />}
        {(pass === null || pass === undefined) && <AlertTriangle className="w-4 h-4 text-amber-600" />}
      </div>
    </div>
  );
}
