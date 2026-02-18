import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { skillApi } from '@/api'

export interface SkillStage {
  key: string
  label: string
  status: string
}

export interface SkillUiLabels {
  project_noun?: string
  create_title?: string
  create_placeholder?: string
  description_placeholder?: string
  output_noun?: string
  output_tab_label?: string
  finalize_action?: string
  [key: string]: string | undefined
}

export interface Skill {
  id: number
  name: string
  icon: string
  description: string
  is_builtin: boolean
  is_enabled: boolean
  role_prompt: string
  strategy_prompt: string
  tool_strategy_prompt: string
  finalization_prompt: string
  output_generation_prompt: string
  stages: SkillStage[]
  ui_labels: SkillUiLabels
  sort_order: number
  created_at: string
  updated_at: string
}

export const useSkillStore = defineStore('skill', () => {
  const skills = ref<Skill[]>([])
  const loading = ref(false)

  const enabledSkills = computed(() => skills.value.filter(s => s.is_enabled))

  async function fetchSkills(enabledOnly = false) {
    loading.value = true
    try {
      const { data } = await skillApi.list({ enabled_only: enabledOnly })
      skills.value = data
    } finally {
      loading.value = false
    }
  }

  async function getSkill(id: number): Promise<Skill> {
    const { data } = await skillApi.get(id)
    return data
  }

  async function createSkill(payload: Partial<Skill>): Promise<Skill> {
    const { data } = await skillApi.create(payload)
    skills.value.push(data)
    return data
  }

  async function updateSkill(id: number, payload: Partial<Skill>): Promise<Skill> {
    const { data } = await skillApi.update(id, payload)
    const idx = skills.value.findIndex(s => s.id === id)
    if (idx >= 0) skills.value[idx] = data
    return data
  }

  async function deleteSkill(id: number) {
    await skillApi.delete(id)
    skills.value = skills.value.filter(s => s.id !== id)
  }

  async function duplicateSkill(id: number): Promise<Skill> {
    const { data } = await skillApi.duplicate(id)
    skills.value.push(data)
    return data
  }

  function getSkillById(id: number | null | undefined): Skill | undefined {
    if (!id) return undefined
    return skills.value.find(s => s.id === id)
  }

  return {
    skills, loading, enabledSkills,
    fetchSkills, getSkill, createSkill, updateSkill, deleteSkill, duplicateSkill,
    getSkillById,
  }
})
