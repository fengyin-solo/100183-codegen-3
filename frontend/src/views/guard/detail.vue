<template>
  <section class="page" data-module="guard-detail">
    <header class="page-head">
      <div>
        <p class="back-line">
          <RouterLink class="link" to="/guard">← 返回第三方施工监护台账</RouterLink>
        </p>
        <h2>{{ project ? project['项目名称'] : '施工监护明细' }}</h2>
        <p class="page-desc">
          查看该项目最新一版施工交底与每次旁站监护明细；在此补录的监护记录会同步更新台账列表上的条数。
        </p>
      </div>
      <div v-if="project" class="page-actions">
        <button class="btn primary" type="button" :disabled="project.status === '已完工'" @click="finishProject">
          {{ project.status === '已完工' ? '项目已完工' : '标注完工' }}
        </button>
      </div>
    </header>

    <div v-if="project" class="detail-grid">
      <article class="detail-card">
        <h3>项目信息</h3>
        <dl class="info-list">
          <div><dt>项目编号</dt><dd>{{ project['项目编号'] }}</dd></div>
          <div><dt>外部单位</dt><dd>{{ project['外部单位'] }}</dd></div>
          <div><dt>涉及管段</dt><dd>{{ project['涉及管段'] }}</dd></div>
          <div><dt>项目状态</dt><dd>
            <span :class="project.status === '已完工' ? 'tag tag-done' : 'tag tag-active'">{{ project.status }}</span>
          </dd></div>
          <div><dt>监护记录</dt><dd><strong>{{ project['监护记录条数'] }}</strong> 条</dd></div>
          <div><dt>未闭环违章</dt><dd>
            <span :class="project['未闭环违章数'] ? 'warn-text' : ''">{{ project['未闭环违章数'] }} 条</span>
          </dd></div>
        </dl>
      </article>

      <article class="detail-card">
        <h3>施工交底（仅展示最新一版）</h3>
        <div v-if="briefing" class="briefing-box">
          <dl class="info-list">
            <div><dt>交底时间</dt><dd>{{ briefing['交底时间'] }}</dd></div>
            <div><dt>交底人</dt><dd>{{ briefing['交底人'] }}</dd></div>
            <div><dt>交底内容</dt><dd class="content-text">{{ briefing['交底内容'] }}</dd></div>
          </dl>
          <button class="btn ghost" type="button" @click="showBriefingForm = !showBriefingForm">
            {{ showBriefingForm ? '取消重新报送' : '重新报送交底（覆盖当前版本）' }}
          </button>
        </div>
        <div v-else class="empty-block">
          <p class="empty-text">该项目还没有交底记录。</p>
          <p class="empty-sub">外部单位在管网保护范围内动工前须先完成施工交底，请补录交底信息后再安排旁站监护。</p>
          <button class="btn primary" type="button" @click="showBriefingForm = true">补录交底</button>
        </div>
        <form v-if="showBriefingForm" class="inline-form" @submit.prevent="submitBriefing">
          <label class="filter-item">
            <span>交底时间</span>
            <input v-model="briefingForm['交底时间']" placeholder="如 2026-09-30 09:00" />
          </label>
          <label class="filter-item">
            <span>交底人</span>
            <input v-model="briefingForm['交底人']" placeholder="我方交底人员" />
          </label>
          <label class="filter-item filter-wide">
            <span>交底内容</span>
            <textarea v-model="briefingForm['交底内容']" rows="2" placeholder="保护范围、禁止事项、应急要求等"></textarea>
          </label>
          <div class="form-actions">
            <button class="btn primary" type="submit">保存交底（作为最新版本）</button>
            <button class="btn ghost" type="button" @click="showBriefingForm = false">取消</button>
          </div>
        </form>
      </article>
    </div>

    <div v-if="project" class="detail-card">
      <h3>旁站监护明细</h3>
      <form class="inline-form" @submit.prevent="addWatch">
        <label class="filter-item">
          <span>监护日期</span>
          <input v-model="watchForm['监护日期']" placeholder="2026-09-30" />
        </label>
        <label class="filter-item">
          <span>监护时段</span>
          <input v-model="watchForm['监护时段']" placeholder="08:00-12:00" />
        </label>
        <label class="filter-item">
          <span>监护人</span>
          <input v-model="watchForm['监护人']" placeholder="现场监护人员" />
        </label>
        <label class="filter-item">
          <span>监护情况</span>
          <select v-model="watchForm['监护情况']">
            <option value="正常">正常</option>
            <option value="发现违章">发现违章</option>
          </select>
        </label>
        <label class="filter-item filter-wide">
          <span>问题描述（违章时必填）</span>
          <textarea v-model="watchForm['问题描述']" rows="2" placeholder="发现违章时写明违章情形与处置要求"></textarea>
        </label>
        <div class="form-actions">
          <button class="btn primary" type="submit">补录监护记录</button>
        </div>
      </form>

      <table class="data-table">
        <thead>
          <tr>
            <th v-for="column in watchColumns" :key="column">{{ column }}</th>
            <th>闭环操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in watchRecords" :key="String(record.id)" :class="{ 'row-violation': record['监护情况'] === '发现违章' && record['闭环状态'] !== '已闭环' }">
            <td>{{ record['监护日期'] }}</td>
            <td>{{ record['监护时段'] }}</td>
            <td>{{ record['监护人'] }}</td>
            <td>
              <span :class="record['监护情况'] === '发现违章' ? 'warn-text' : ''">{{ record['监护情况'] }}</span>
            </td>
            <td>{{ record['问题描述'] || '—' }}</td>
            <td>
              <span :class="record['闭环状态'] === '已闭环' ? 'tag tag-done' : 'tag tag-warn'">{{ record['闭环状态'] }}</span>
            </td>
            <td>
              <button
                v-if="record['监护情况'] === '发现违章' && record['闭环状态'] !== '已闭环'"
                class="link"
                type="button"
                @click="closeWatch(record.id)"
              >
                确认闭环
              </button>
              <span v-else class="muted-text">—</span>
            </td>
          </tr>
          <tr v-if="!watchRecords.length">
            <td :colspan="watchColumns.length + 1" class="empty-state">
              该项目还没有旁站监护记录，可在上方补录第一次旁站情况。
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else-if="!loading" class="empty-block">
      <p class="empty-text">未找到该施工项目。</p>
      <RouterLink class="link" to="/guard">返回台账列表</RouterLink>
    </div>

    <footer class="page-foot">
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
      <span v-else-if="noticeMessage" class="notice-text">{{ noticeMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import { request } from '@/api/client'

type Briefing = {
  交底时间: string
  交底人: string
  交底内容: string
}

type WatchRecord = {
  id: number
  监护日期: string
  监护时段: string
  监护人: string
  监护情况: string
  问题描述: string
  闭环状态: string
}

type ProjectDetail = {
  id: number
  status: string
  项目编号: string
  项目名称: string
  外部单位: string
  涉及管段: string
  监护记录条数: number
  未闭环违章数: number
  交底记录: Briefing | null
  监护记录: WatchRecord[]
}

const route = useRoute()
const projectId = Number(route.params.id)
const ENDPOINT = `/api/guard/${projectId}`

const watchColumns = ['监护日期', '监护时段', '监护人', '监护情况', '问题描述', '闭环状态']

const project = ref<ProjectDetail | null>(null)
const watchRecords = ref<WatchRecord[]>([])
const briefing = ref<Briefing | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const noticeMessage = ref('')
const showBriefingForm = ref(false)

const briefingForm = reactive({ 交底时间: '', 交底人: '', 交底内容: '' })
const watchForm = reactive({
  监护日期: '',
  监护时段: '',
  监护人: '',
  监护情况: '正常',
  问题描述: '',
})

async function reload() {
  errorMessage.value = ''
  try {
    const response = await request(ENDPOINT)
    if (response.status === 404) {
      project.value = null
      loading.value = false
      return
    }
    if (!response.ok) {
      throw new Error('项目明细读取失败')
    }
    const detail = (await response.json()) as ProjectDetail
    project.value = detail
    watchRecords.value = detail['监护记录'] ?? []
    briefing.value = detail['交底记录']
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '项目明细读取失败'
  } finally {
    loading.value = false
  }
}

async function submitBriefing() {
  errorMessage.value = ''
  noticeMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/briefing`, {
      method: 'POST',
      body: JSON.stringify({ values: { ...briefingForm } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '交底保存失败')
    }
    noticeMessage.value = payload.message
    showBriefingForm.value = false
    Object.assign(briefingForm, { 交底时间: '', 交底人: '', 交底内容: '' })
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '交底保存失败'
  }
}

async function addWatch() {
  errorMessage.value = ''
  noticeMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/watch`, {
      method: 'POST',
      body: JSON.stringify({ values: { ...watchForm } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '监护记录补录失败')
    }
    noticeMessage.value = payload.message
    Object.assign(watchForm, { 监护日期: '', 监护时段: '', 监护人: '', 监护情况: '正常', 问题描述: '' })
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '监护记录补录失败'
  }
}

async function closeWatch(watchId: number) {
  errorMessage.value = ''
  noticeMessage.value = ''
  try {
    const response = await request(`/api/guard/watch/${watchId}/close`, {
      method: 'POST',
      body: JSON.stringify({ values: { project_id: projectId } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '闭环操作失败')
    }
    noticeMessage.value = payload.message
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '闭环操作失败'
  }
}

async function finishProject() {
  errorMessage.value = ''
  noticeMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/finish`, { method: 'POST' })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '完工标注失败')
    }
    noticeMessage.value = payload.message
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '完工标注失败'
  }
}

onMounted(reload)
</script>
