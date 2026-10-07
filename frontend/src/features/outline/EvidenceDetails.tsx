import type { OutlinePage } from '@/features/outline/types'
import type { ProjectDetail } from '@/features/projects/types'

const compact = (value: string) => value.replace(/\s+/g, '')

/** 用要点原文绑定引用。用户改写后立刻失效，避免旧来源冒充新结论的证据。 */
export function EvidenceDetails({ page, project }: { page: OutlinePage; project: ProjectDetail }) {
  const sources = new Map(project.sources.flatMap((source, i) => source.sections.map((section, j) => [
    `S${i + 1}:${j + 1}` as string, { ...section, filename: source.filename ?? '粘贴材料', kind: source.kind },
  ] as const)))
  const rows = page.key_points.map((point) => {
    const evidence = page.point_evidence?.find((item) => item.point === point)
    const source = evidence?.ref ? sources.get(evidence.ref) : undefined
    const quote = compact(evidence?.quote ?? '')
    const valid = evidence?.kind === 'source' && source && source.kind !== 'topic'
      && quote.length >= 4 && compact(source.text).includes(quote)
    return { point, evidence, source, valid }
  })
  const missing = rows.filter((row) => !row.valid && row.evidence?.kind !== 'inference').length
  return (
    <details className="mt-3 rounded-xl border border-line bg-surface-soft/50 p-3 text-xs">
      <summary className="cursor-pointer font-medium text-accent">
        查看要点依据 · {rows.filter((row) => row.valid).length} 条摘录匹配
        {missing > 0 ? ` · ${missing} 条待补充` : ''}
      </summary>
      <p className="mt-2 leading-relaxed text-ink-muted">摘录匹配仅说明原文存在，请核对原文是否支持结论。修改要点后需重新核对。</p>
      <ul className="mt-3 space-y-3">
        {rows.map(({ point, evidence, source, valid }, index) => (
          <li key={index} className="border-t border-line pt-3">
            <p className="font-medium leading-relaxed text-ink">{point}</p>
            {valid && source ? <>
              <p className="mt-1 text-accent">材料摘录 · {evidence?.ref} · {source.filename} · {source.locator}</p>
              <blockquote className="mt-2 border-l-2 border-accent/40 pl-3 leading-relaxed text-ink-soft">{evidence?.quote}</blockquote>
              <details className="mt-2 text-ink-muted"><summary className="cursor-pointer">展开原文上下文</summary>
                <p className="mt-2 whitespace-pre-wrap break-words leading-relaxed">{source.text}</p>
              </details>
            </> : <p className="mt-1 text-warning">{evidence?.kind === 'inference' ? 'AI 推断 · 需人工核对' : '待补充 · 没有有效摘录，请补充对应材料或重新生成大纲'}</p>}
          </li>
        ))}
      </ul>
    </details>
  )
}
