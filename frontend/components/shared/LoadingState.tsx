export function LoadingState({ label = "Bringing your Day One picture together…" }: { label?: string }) {
  return <div className="grid min-h-[60vh] place-items-center"><div className="text-center"><div className="mx-auto mb-4 h-9 w-9 animate-spin rounded-full border-2 border-[#173f35]/15 border-t-[#173f35]" /><p className="text-sm text-[#6b7571]">{label}</p></div></div>;
}
