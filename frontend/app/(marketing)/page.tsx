import Link from "next/link";
import { CheckCircle2, FileText, Shirt, Palette, Ruler } from "lucide-react";
import RegMarks from "@/components/RegMarks";
import BrandMark from "@/components/BrandMark";

const CHECKS = [
  { icon: Ruler, label: "DPI / resolution" },
  { icon: FileText, label: "Crop marks & bleed" },
  { icon: CheckCircle2, label: "White edges & fonts" },
  { icon: Palette, label: "Color palette + closest color reference" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-stone-50 text-stone-900">
      <header className="border-b border-stone-200 bg-white">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <BrandMark size="lg" />
          <nav className="flex items-center gap-6 text-sm">
            <Link href="/login" className="text-stone-600 hover:text-stone-900">
              Log in
            </Link>
            <Link href="/signup" className="bg-stone-900 text-white px-4 py-2 rounded hover:bg-stone-800">
              Get started
            </Link>
          </nav>
        </div>
      </header>

      <section className="max-w-5xl mx-auto px-6 py-24 text-center">
        <p className="text-xs uppercase tracking-widest text-blue-700 font-semibold mb-4">
          Print production QA, automated
        </p>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-6">
          Catch print-ready file problems<br />before they hit the press.
        </h1>
        <p className="text-stone-600 max-w-xl mx-auto mb-10">
          Upload a PDF or image and get a full production QA report — resolution, bleed, crop
          marks, fonts, color palette — plus a standalone logo checker for apparel printing.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link href="/signup" className="bg-blue-700 text-white px-6 py-3 rounded font-medium hover:bg-blue-800">
            Start checking files
          </Link>
          <Link href="/login" className="border border-stone-300 px-6 py-3 rounded font-medium hover:bg-white">
            Log in
          </Link>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 pb-24 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {CHECKS.map((c) => (
          <div key={c.label} className="relative bg-white border border-stone-200 rounded p-6">
            <RegMarks />
            <c.icon className="w-6 h-6 text-blue-700 mb-3" />
            <p className="text-sm font-medium">{c.label}</p>
          </div>
        ))}
      </section>

      <section className="max-w-5xl mx-auto px-6 pb-24">
        <div className="relative bg-white border border-stone-200 rounded p-10 text-center">
          <RegMarks />
          <Shirt className="w-8 h-8 text-stone-400 mx-auto mb-3" />
          <h2 className="text-lg font-bold tracking-tight mb-2">Apparel logo checker</h2>
          <p className="text-sm text-stone-500 max-w-md mx-auto mb-6">
            Upload a logo and get a suitability verdict for apparel printing — DPI, color count,
            transparency, and vector vs. raster — with specific reasons, not just pass/fail.
          </p>
          <Link href="/signup" className="bg-stone-900 text-white text-sm px-4 py-2 rounded inline-block">
            Try it free
          </Link>
        </div>
      </section>

      <footer className="border-t border-stone-200 py-8 text-center text-xs text-stone-400">
        PressCheck — Print QA Check
      </footer>
    </div>
  );
}
