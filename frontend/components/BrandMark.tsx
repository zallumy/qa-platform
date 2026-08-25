export default function BrandMark({ size = "sm" }: { size?: "sm" | "lg" }) {
  const dims = size === "lg" ? "w-6 h-6" : "w-4 h-4";
  const text = size === "lg" ? "text-lg" : "text-sm";
  return (
    <div className="flex items-center gap-2">
      <svg viewBox="0 0 16 16" className={dims}>
        <circle cx="8" cy="8" r="4.5" fill="none" className="stroke-blue-700" strokeWidth="1.2" />
        <line x1="8" y1="0" x2="8" y2="16" className="stroke-blue-700" strokeWidth="1.2" />
        <line x1="0" y1="8" x2="16" y2="8" className="stroke-blue-700" strokeWidth="1.2" />
      </svg>
      <span className={`font-bold tracking-tight ${text}`}>PRESSCHECK</span>
    </div>
  );
}
