import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { request } from '@/api/client'
import { Button } from '@/components/ui/Button'
import { errorMessage } from '@/lib/errors'

export function MaterialSupplement({ projectId, onRegenerate, disabled }: {
  projectId: string; onRegenerate: () => void; disabled: boolean
}) {
  const [content, setContent] = useState('')
  const cache = useQueryClient()
  const add = useMutation({
    mutationFn: () => request(`/projects/${projectId}/sources`, {
      method: 'POST', body: JSON.stringify({ kind: 'text', content: content.trim() }),
    }),
    onSuccess: async () => {
      setContent('')
      await cache.invalidateQueries({ queryKey: ['projects', projectId] })
      onRegenerate()
    },
  })
  return <details className="rounded-2xl border border-line bg-surface p-4">
    <summary className="cursor-pointer text-sm font-medium">补充缺失材料</summary>
    <p className="mt-2 text-xs leading-relaxed text-ink-muted">补上个人分工、实验记录或结果依据后重新生成大纲。当前大纲中的手动修改会被替换。</p>
    <textarea aria-label="补充材料" value={content} maxLength={20000} rows={5}
      disabled={disabled || add.isPending} onChange={(event) => setContent(event.target.value)}
      placeholder="粘贴可以核对的原始记录，不填写虚构数据"
      className="mt-3 w-full rounded-lg border border-line p-2 text-xs leading-relaxed" />
    <Button size="sm" className="mt-2" disabled={disabled || add.isPending || !content.trim()}
      onClick={() => add.mutate()}>{add.isPending ? '正在保存…' : '保存材料并重新生成'}</Button>
    {add.isError && <p role="alert" className="mt-2 text-xs text-negative">{errorMessage(add.error)}</p>}
  </details>
}
