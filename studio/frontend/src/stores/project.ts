import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectApi } from '@/api'

export interface Project {
  id: number
  title: string
  description: string
  status: string
  plan_content: string
  plan_version: number
  github_issue_number: number | null
  github_pr_number: number | null
  branch_name: string | null
  preview_port: number | null
  discussion_model: string
  implementation_model: string
  tool_permissions: string[] | null
  created_by: string
  created_at: string
  updated_at: string
  message_count: number
}

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const loading = ref(false)

  async function fetchProjects() {
    loading.value = true
    try {
      const { data } = await projectApi.list()
      projects.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(id: number) {
    loading.value = true
    try {
      const { data } = await projectApi.get(id)
      currentProject.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function createProject(payload: any) {
    const { data } = await projectApi.create(payload)
    projects.value.unshift(data)
    return data
  }

  async function updateProject(id: number, payload: any) {
    const { data } = await projectApi.update(id, payload)
    currentProject.value = data
    const idx = projects.value.findIndex(p => p.id === id)
    if (idx >= 0) projects.value[idx] = data
    return data
  }

  async function deleteProject(id: number) {
    await projectApi.delete(id)
    projects.value = projects.value.filter(p => p.id !== id)
    if (currentProject.value?.id === id) currentProject.value = null
  }

  return {
    projects, currentProject, loading,
    fetchProjects, fetchProject, createProject, updateProject, deleteProject,
  }
})
