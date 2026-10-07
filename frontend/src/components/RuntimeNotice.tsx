import { useQuery } from '@tanstack/react-query'
import { request } from '@/api/client'
import { Link } from 'react-router'
import { useAuthStore } from '@/features/auth/store'

export function RuntimeNotice() {
  const user = useAuthStore(state => state.user)
  const personal = useQuery({ queryKey: ['model-settings', user?.id], enabled: Boolean(user),
    queryFn: () => request<{ custom: boolean }>('/model-settings') })
  const health = useQuery({ queryKey: ['runtime'], queryFn: () => request<{
    generation_mode: 'demo' | 'live'; llm_configured: boolean
  }>('/health'), staleTime: 30_000 })
  if (!health.data || (user && personal.data?.custom)) return null
  const demo = health.data.generation_mode === 'demo'
  if (!demo && health.data.llm_configured) return null
  return <div role="status" className="border-b border-line bg-accent-soft px-5 py-2 text-center text-xs text-accent">
    {demo ? '演示模式 · 使用规则摘录材料，不调用 AI 模型；可体验大纲、编辑、来源查看与导出。AI 修改需切换真实模型模式。'
      : '尚未配置模型密钥，请填写自己的 API Key。'}
    {user && <Link to="/settings/model" className="ml-2 underline">模型设置</Link>}
  </div>
}
