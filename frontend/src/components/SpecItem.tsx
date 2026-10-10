import type { ReactNode } from 'react';

interface SpecItemProps {
  label: string;
  children: ReactNode;
}

/** Плитка характеристики внутри <dl>: подпись и значение */
export default function SpecItem({ label, children }: SpecItemProps) {
  return (
    <div className="listing-specs__item min-w-0 rounded-[var(--radius-md)] bg-[var(--surface-hover)] px-2.5 py-3 sm:p-3">
      <dt className="text-xs text-[var(--text-secondary)]">{label}</dt>
      {/* На 375px длинное слово («გარემონტებული») крупным шрифтом не помещается в плитку и рвётся */}
      <dd className="mt-1 break-words text-[13px] font-semibold sm:text-base">{children}</dd>
    </div>
  );
}
