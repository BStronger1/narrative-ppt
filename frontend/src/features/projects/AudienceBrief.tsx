import { usePresentationPresets, type PresentationBrief } from './audience'

export function AudienceBrief({ value, onChange, onAudienceChange, disabled = false }: {
  value: PresentationBrief; onChange: (value: PresentationBrief) => void
  onAudienceChange?: (audience: string) => void; disabled?: boolean
}) {
  const presets = usePresentationPresets()
  const profile = presets.data?.profiles.find(item => item.id === value.audience_profile)
  const update = (patch: Partial<PresentationBrief>) => onChange({ ...value, ...patch, narrative_enabled: true })
  const input = 'mt-2 w-full rounded-xl border border-line bg-surface-soft px-3 py-2 text-sm focus:outline-accent'
  return <fieldset disabled={disabled} className="space-y-5 disabled:opacity-60">
    <div><h2 className="text-base font-semibold">这次讲给谁听？</h2><p className="mt-1 text-xs leading-5 text-ink-muted">先选择听众，再结合材料规划讲述顺序。预设可以调整，并非固定模板。</p></div>
    {presets.isError && <p role="alert" className="text-xs text-negative">听众预设加载失败。<button type="button" className="underline" onClick={() => void presets.refetch()}>重试</button></p>}
    {presets.isPending && <p className="text-xs text-ink-muted">正在加载听众预设…</p>}
    <div className="grid gap-2 sm:grid-cols-3">{presets.data?.profiles.map(item => <button key={item.id} type="button" aria-pressed={value.audience_profile === item.id}
      onClick={() => { update({ audience_profile: item.id, scenario: item.id === 'academic' ? 'defense' : 'general' }); onAudienceChange?.(item.id === 'custom' ? '' : item.label) }}
      className={`rounded-xl border p-3 text-left transition-colors ${value.audience_profile === item.id ? 'border-accent bg-accent-soft' : 'border-line hover:border-line-strong'}`}>
      <span className="text-sm font-medium">{item.label}</span><span className="mt-1 block text-xs leading-5 text-ink-muted">{item.description}</span>
    </button>)}</div>
    {profile && <div className="rounded-xl bg-surface-soft p-3 text-xs leading-6 text-ink-soft"><p>通常关心：{profile.needs.join('；')}</p><p>建议顺序：{profile.arc.join(' → ')}</p></div>}
    <div className="grid gap-4 sm:grid-cols-3">
      <label className="text-xs font-medium">听众知识基础<select value={value.knowledge_level ?? 'auto'} onChange={e => update({ knowledge_level: e.target.value as PresentationBrief['knowledge_level'] })} className={input}><option value="auto">由 AI 结合材料判断</option><option value="newcomer">首次接触，需要例子</option><option value="familiar">了解基础，关注重点</option><option value="expert">熟悉领域，关注细节</option></select></label>
      <label className="text-xs font-medium">讲述时长（分钟）<input type="number" min={1} max={60} value={value.duration_minutes ?? 5} className={input} onChange={e => update({ duration_minutes: Math.min(60, Math.max(1, Number(e.target.value) || 1)) })} /></label>
      <label className="text-xs font-medium">视觉表达<select value={value.visual_style ?? 'clean'} onChange={e => update({ visual_style: e.target.value as PresentationBrief['visual_style'] })} className={input}><option value="clean">清晰简洁</option><option value="editorial">故事讲述</option><option value="technical">结构分析</option></select></label>
    </div>
    <label className="block text-xs font-medium">希望听众理解什么，或做出什么决定？<input maxLength={1000} value={value.focus ?? ''} onChange={e => update({ focus: e.target.value })} className={input} placeholder="例如：理解方案取舍，并同意开展小范围试点" /></label>
    <details><summary className="cursor-pointer text-xs text-accent">调整讲述要求 / 查看设计依据</summary>
      <label className="mt-3 block text-xs">补充或覆盖预设顺序<textarea rows={3} maxLength={1500} value={value.narrative_overrides ?? ''} onChange={e => update({ narrative_overrides: e.target.value })} className={input} placeholder="例如：先给结论，省略行业背景；重点解释风险，不用营销式措辞" /></label>
      <p className="mt-2 text-xs leading-5 text-ink-muted">参考认知负荷、多媒体学习和精细加工可能性理论安排信息。听众期望是设计假设，实际效果需要反馈验证。</p>
      {Object.entries(presets.data?.principles ?? {}).map(([id, principle]) => <p key={id} className="mt-2 text-xs leading-5 text-ink-muted"><a href={principle.url} target="_blank" rel="noreferrer" className="underline">{principle.label} · {principle.citation}</a>：{principle.application}</p>)}
    </details>
  </fieldset>
}
