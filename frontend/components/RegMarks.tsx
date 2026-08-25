// Registration-mark corner motif: the app's signature visual element,
// borrowed directly from real print registration marks.
export default function RegMarks({ color = "stroke-blue-700" }: { color?: string }) {
  const Mark = ({ className }: { className: string }) => (
    <svg viewBox="0 0 16 16" className={`absolute w-3 h-3 ${className}`}>
      <circle cx="8" cy="8" r="4.5" fill="none" className={color} strokeWidth="1" />
      <line x1="8" y1="0" x2="8" y2="16" className={color} strokeWidth="1" />
      <line x1="0" y1="8" x2="16" y2="8" className={color} strokeWidth="1" />
    </svg>
  );
  return (
    <>
      <Mark className="-top-1.5 -left-1.5" />
      <Mark className="-top-1.5 -right-1.5" />
      <Mark className="-bottom-1.5 -left-1.5" />
      <Mark className="-bottom-1.5 -right-1.5" />
    </>
  );
}
