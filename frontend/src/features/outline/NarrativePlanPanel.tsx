import type { components } from '@/api/schema'
import { usePresentationPresets } from '@/features/projects/audience'

export function NarrativePlanPanel({ plan }: { plan: components['schemas']['NarrativePlan'] }) {
  const presets = usePresentationPresets()
  return <section className="mb-5 rounded-2xl border border-line bg-surface p-5 shadow-card">
    <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-semibold">这份 PPT 的讲述方案</h2><span className="rounded-full bg-accent-soft px-3 py-1 text-xs text-accent">{plan.source === 'ai' ? 'AI 结合材料规划' : '预设建议 · 请复核'}</span></div>
    <p className="mt-3 text-sm font-medium">{plan.throughline}</p>
    <p className="mt-2 text-xs leading-6 text-ink-muted">面向 {plan.audience_summary} · 关注 {plan.audience_needs.join('；')}</p>
    <ol className="mt-4 flex flex-wrap gap-2">{plan.arc.map((step, index) => <li key={index} className="rounded-lg bg-surface-soft px-3 py-2 text-xs"><span className="mr-2 text-accent">{index + 1}</span>{step}</li>)}</ol>
    <div className="mt-4 grid gap-3 text-xs leading-6 sm:grid-cols-2"><p><strong>如何开场：</strong>{plan.opening}</p><p><strong>如何收尾：</strong>{plan.closing_action}</p></div>
    <details className="mt-3 text-xs leading-6 text-ink-muted"><summary className="cursor-pointer text-accent">为什么这样讲 / 待确认假设</summary><p className="mt-2">{plan.rationale}</p><p>视觉安排：{plan.visual_strategy}</p>
      {plan.assumptions?.map((item, i) => <p key={i}>待确认：{item}</p>)}
      <div className="mt-2 flex flex-wrap gap-3">{plan.principles?.map(id => {
        const item = presets.data?.principles[id]
        return item ? <a key={id} href={item.url} target="_blank" rel="noreferrer" className="underline">{item.label} · {item.citation}</a> : null
      })}</div><p>以上是表达设计建议，不是对听众个体的心理测量。</p>
    </details>
  </section>
}
