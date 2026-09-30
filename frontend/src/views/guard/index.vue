<template>
  <section class="page" data-module="guard">
    <header class="page-head">
      <div>
        <h2>第三方施工监护台账</h2>
        <p class="page-desc">外部单位在管网保护范围内的施工交底与旁站监护集中呈现；未交底项目单独高亮，完工后自动退出待监护视图。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记施工项目</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <div class="scope-tabs" role="tablist">
        <button
          v-for="tab in scopeTabs"
          :key="tab.value"
          type="button"
          class="btn"
          :class="{ primary: scope === tab.value }"
          @click="switchScope(tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>
      <label v-if="scope === 'all'" class="filter-item">
        <span>项目状态</span>
        <select v-model="status">
          <option value="">全部状态</option>
          <option value="在建">在建</option>
          <option value="已完工">已完工</option>
        </select>
      </label>
      <label class="filter-item">
        <span>关键字</span>
        <input v-model="keyword" placeholder="按项目名称 / 编号 / 外部单位检索" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)" :class="{ 'row-warning': !row['是否已交底'] }">
          <td>{{ row['项目编号'] }}</td>
          <td>{{ row['项目名称'] }}</td>
          <td>{{ row['外部单位'] }}</td>
          <td>{{ row['涉及管段'] }}</td>
          <td>
            <span v-if="row['交底时间']">{{ row['交底时间'] }}</span>
            <span v-else class="tag tag-warning">尚未交底</span>
          </td>
          <td>{{ row['监护人'] ?? '—' }}</td>
          <td>
            <strong>{{ row['监护记录条数'] }}</strong> 条
            <span v-if="row['未闭环违章数']" class="tag tag-danger">违章未闭环 {{ row['未闭环违章数'] }}</span>
          </td>
          <td>
            <span class="tag" :class="row['项目状态'] === '在建' ? 'tag-active' : 'tag-done'">{{ row['项目状态'] }}</span>
          </td>
          <td class="row-actions">
            <RouterLink class="link" :to="`/guard/${row.id}`">查看明细</RouterLink>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">
            {{ scope === 'pending' ? '待监护视图暂无在建施工项目' : '暂无施工监护项目，可先登记施工项目并补录交底信息' }}
          </td>
        </tr>
      </tbody>
    </table>

    <p v-if="scope === 'pending' && rows.length" class="empty-hint">
      高亮行为尚未施工交底的项目，需尽快组织交底；运营概览中的「在建监护」数与本视图条数一致（{{ total }}）。
    </p>

    <footer class="page-foot">
      <span>共 {{ total }} 个施工项目</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <div v-if="creating" class="modal-mask" @click.self="creating = false">
      <form class="modal-card" @submit.prevent="submitCreate">
        <h3>登记施工项目</h3>
        <label v-for="field in createFields" :key="field" class="filter-item">
          <span>{{ field }}</span>
          <input v-model="createForm[field]" :placeholder="`请输入${field}`" />
        </label>
        <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
        <div class="modal-actions">
          <button class="btn ghost" type="button" @click="creating = false">取消</button>
          <button class="btn primary" type="submit">保存并进入待监护</button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | boolean | null>

const ENDPOINT = '/api/guard/projects'
const columns = ['项目编号', '项目名称', '外部单位', '涉及管段', '交底时间', '监护人', '监护记录条数', '项目状态']
const scopeTabs = [
  { label: '待监护（在建）', value: 'pending' },
  { label: '全部项目', value: 'all' },
] as const
const createFields = ['项目名称', '外部单位', '涉及管段'] as const

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const keyword = ref('')
const scope = ref<'pending' | 'all'>('pending')
const status = ref('')
const creating = ref(false)
const createForm = reactive<Record<string, string>>({ 项目名称: '', 外部单位: '', 涉及管段: '' })
const stats = ref([
  { label: '在建监护', value: 0 },
  { label: '未交底项目', value: 0 },
  { label: '未闭环违章', value: 0 },
  { label: '监护记录总数', value: 0 },
])

function openCreate() {
  errorMessage.value = ''
  createFields.forEach((field) => { createForm[field] = '' })
  creating.value = true
}

function switchScope(next: 'pending' | 'all') {
  scope.value = next
  status.value = ''
  void reload()
}

function resetFilters() {
  keyword.value = ''
  status.value = ''
  void reload()
}

async function submitCreate() {
  errorMessage.value = ''
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: { ...createForm } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload?.message ? String(payload.message) : '施工项目登记失败')
    }
    creating.value = false
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '施工项目登记失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams({ scope: scope.value })
  if (keyword.value.trim()) query.set('keyword', keyword.value.trim())
  if (scope.value === 'all' && status.value) query.set('status', status.value)
  try {
    const response = await request(`${ENDPOINT}?${query.toString()}`)
    if (!response.ok) throw new Error('施工监护台账读取失败')
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    if (scope.value === 'pending') {
      // 卡片口径与待监护视图同源；监护记录总数汇总自视图各项目。
      stats.value[0].value = total.value
      stats.value[1].value = rows.value.filter((row) => !row['是否已交底']).length
      stats.value[2].value = rows.value.reduce((sum, row) => sum + Number(row['未闭环违章数'] ?? 0), 0)
      stats.value[3].value = rows.value.reduce((sum, row) => sum + Number(row['监护记录条数'] ?? 0), 0)
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '施工监护台账读取失败'
  }
}

onMounted(reload)
</script>

<style scoped>
.scope-tabs { display: flex; gap: 6px; align-items: flex-end; }
.empty-hint { margin: 8px 0 0; font-size: 12px; color: var(--muted); }
.row-warning td { background: #fff7ed; }
.tag { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 12px; border: 1px solid var(--border); }
.tag-warning { color: #b42318; border-color: #fda29b; background: #fef3f2; }
.tag-danger { margin-left: 6px; color: #b42318; border-color: #fda29b; background: #fef3f2; }
.tag-active { color: #b54708; border-color: #fec84b; background: #fffaeb; }
.tag-done { color: #027a48; border-color: #6ce9a6; background: #ecfdf3; }
.modal-mask { position: fixed; inset: 0; background: rgba(16, 24, 40, 0.45); display: flex; align-items: center; justify-content: center; z-index: 20; }
.modal-card { background: #fff; border-radius: 10px; padding: 18px 20px; width: 420px; display: flex; flex-direction: column; gap: 10px; }
.modal-card h3 { margin: 0; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
</style>
