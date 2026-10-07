import { useOutline } from '@/features/outline/api'
import { EvidenceDetails } from '@/features/outline/EvidenceDetails'
import type { ProjectDetail } from '@/features/projects/types'
import type { DeckSlide } from '@/features/deck/types'

export function EvidencePanel({ project, slide }: { project: ProjectDetail; slide: DeckSlide }) {
  const outline = useOutline(project.id)
  const page = outline.data?.pages.find((item) => item.id === slide.outline_page_id)
  return <div>
    <h2 className="text-sm font-semibold">内容来源</h2>
    <p className="mt-2 text-xs leading-relaxed text-ink-muted">这里展示本页大纲要点的证据。生成正文或手动编辑可能引入新表述，仍需逐项核对；导出时这些引用会附在演讲者备注中。</p>
    {outline.isPending ? <p className="mt-4 text-xs">正在读取来源…</p> :
      outline.isError ? <button className="mt-4 text-xs text-accent" onClick={() => void outline.refetch()}>来源加载失败，点击重试</button> :
      page ? <EvidenceDetails page={page} project={project} /> :
      <p className="mt-4 text-xs text-warning">该页暂无大纲来源。</p>}
    {slide.speaker_notes && <div className="mt-6 border-t border-line pt-4">
      <h3 className="text-sm font-medium">讲稿提示</h3>
      <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-ink-soft">{slide.speaker_notes}</p>
    </div>}
  </div>
}
