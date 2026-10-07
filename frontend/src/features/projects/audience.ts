import { useQuery } from '@tanstack/react-query'
import { request } from '@/api/client'
import type { components } from '@/api/schema'

export type PresentationBrief = components['schemas']['PresentationBrief']
export const DEFAULT_BRIEF: PresentationBrief = {
  scenario: 'defense', duration_minutes: 5, focus: '', narrative_enabled: true,
  audience_profile: 'academic', knowledge_level: 'auto', narrative_overrides: '', visual_style: 'clean',
}
export interface PresentationPresets {
  profiles: { id: NonNullable<PresentationBrief['audience_profile']>; label: string; description: string; needs: string[]; arc: string[] }[]
  principles: Record<string, { label: string; application: string; citation: string; url: string }>
  styles: Record<string, string>; note: string
}
export function usePresentationPresets() {
  return useQuery({ queryKey: ['presentation-presets'], queryFn: () => request<PresentationPresets>('/presentation-presets'), staleTime: Infinity })
}
