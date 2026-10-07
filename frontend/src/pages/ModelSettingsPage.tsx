import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { request } from '@/api/client'
import { Button } from '@/components/ui/Button'

export interface ModelSettings {
  custom: boolean; base_url: string; model: string; has_api_key: boolean
  default_available: boolean; allowed_hosts: string[]
}

export default function ModelSettingsPage() {
  const cache = useQueryClient()
  const [saved, setSaved] = useState<ModelSettings | null>(null)
  const [baseUrl, setBaseUrl] = useState('')
  const [model, setModel] = useState('')
  const [key, setKey] = useState('')
  const [models, setModels] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const apply = (data: ModelSettings) => {
    setSaved(data); setBaseUrl(data.base_url); setModel(data.model); setKey(''); setModels([])
  }
  useEffect(() => {
    let active = true
    request<ModelSettings>('/model-settings').then(data => { if (active) apply(data) })
      .catch(() => { if (active) setMessage('设置加载失败，请刷新重试。') })
    return () => { active = false }
  }, [])
  async function perform(action: 'save' | 'test' | 'models' | 'reset') {
    setBusy(true); setMessage('')
    const body = JSON.stringify({ base_url: baseUrl, model: model || 'list-models', ...(key ? { api_key: key } : {}) })
    try {
      if (action === 'save' || action === 'reset') {
        const data = await request<ModelSettings>('/model-settings', {
          method: action === 'save' ? 'PUT' : 'DELETE', ...(action === 'save' ? { body } : {}),
        })
        apply(data)
        await cache.invalidateQueries({ queryKey: ['model-settings'] })
        setMessage(action === 'save' ? '已保存。之后发起的生成和修改将使用你的模型。' : '已删除个人密钥，恢复默认模型。')
      } else if (action === 'test') {
        const data = await request<{ message: string }>('/model-settings/test', { method: 'POST', body })
        setMessage(data.message + '；保存后生效。')
      } else {
        const data = await request<{ models: string[] }>('/model-settings/models', { method: 'POST', body })
        setModels(data.models)
        setMessage(data.models.length ? `已获取 ${data.models.length} 个模型，可在下方选择。` : '服务商未返回模型，请手动填写。')
      }
    } catch (error) { setMessage(error instanceof Error ? error.message : '操作失败，请重试') }
    finally { setBusy(false) }
  }
  const inputClass = 'w-full rounded-xl border border-line bg-surface px-4 py-3 text-sm outline-none focus:border-accent'
  return <section className="mx-auto max-w-2xl space-y-6 px-6 py-10">
    <div><h1 className="text-2xl font-semibold">模型设置</h1>
      <p className="mt-2 text-sm text-ink-muted">选择模型，使用自己的 API Key 生成 PPT。设置仅对当前账号生效。</p></div>
    {saved && <p className="rounded-xl bg-surface-soft p-4 text-sm">当前使用：{saved.custom ? '个人模型' : '系统默认模型'} · {saved.model}
      {!saved.custom && !saved.default_available && '（尚未配置，请填写个人密钥）'}</p>}
    <form className="space-y-5" onSubmit={event => { event.preventDefault(); void perform('save') }}>
      <fieldset disabled={busy || !saved} className="space-y-5 disabled:opacity-60">
        <label className="block space-y-2"><span className="text-sm font-medium">API 服务地址（OpenAI 兼容）</span>
          <input required type="url" className={inputClass} value={baseUrl} onChange={e => { setBaseUrl(e.target.value); setModels([]) }} placeholder="https://api.deepseek.com/v1" />
          <span className="block text-xs leading-5 text-ink-muted">支持 {saved?.allowed_hosts.join('、')}。填写服务商提供的完整基础地址，其他服务可由管理员添加。</span>
        </label>
        <label className="block space-y-2"><span className="text-sm font-medium">你的 API Key</span>
          <input type="password" autoComplete="new-password" spellCheck={false} className={inputClass} value={key} onChange={e => setKey(e.target.value)} placeholder={saved?.has_api_key ? '已加密保存；留空可继续使用（更换地址需重新填写）' : '填写服务商签发的 API Key'} />
          <span className="block text-xs text-ink-muted">密钥加密保存在服务器，不会回显。请在 HTTPS 或可信网络下填写。</span>
        </label>
        <label className="block space-y-2"><span className="text-sm font-medium">模型名称</span>
          <input required className={inputClass} value={model} onChange={e => setModel(e.target.value)} placeholder="填写服务商提供的模型 ID" />
        </label>
        <Button type="button" variant="ghost" onClick={() => void perform('models')}>获取可用模型</Button>
        {models.length > 0 && <label className="block space-y-2"><span className="text-sm">从可用模型中选择</span><select className={inputClass} value={models.includes(model) ? model : ''} onChange={e => setModel(e.target.value)}><option value="" disabled>请选择模型</option>{models.map(id => <option key={id} value={id}>{id}</option>)}</select></label>}
        <div className="flex flex-wrap gap-3">
          <Button type="submit">{busy ? '处理中…' : '保存设置'}</Button>
          <Button type="button" variant="ghost" onClick={() => void perform('test')}>测试连接</Button>
          {saved?.custom && <Button type="button" variant="ghost" onClick={() => void perform('reset')}>删除密钥并恢复默认</Button>}
        </div>
      </fieldset>
    </form>
    {message && <p role="status" className="rounded-xl border border-line p-4 text-sm">{message}</p>}
    <p className="text-xs leading-6 text-ink-muted">适用于大纲生成、页面内容、AI 修改与重新排版。模型需支持 JSON 输出；连接测试会发起一次小额请求。调用费用由你的服务商账户承担，已开始的任务继续使用原设置。</p>
  </section>
}
