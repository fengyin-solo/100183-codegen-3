<template>
  <section class="page" data-module="guard">
    <header class="page-head">
      <div>
        <h2>第三方施工监护台账</h2>
        <p class="page-desc">集中呈现外部单位在管网保护范围内的施工交底与旁站监护：按项目核对交底时间、涉及管段、监护人与监护记录条数，未交底项目已高亮提示。</p>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <div class="scope-bar">
      <button
        class="btn"
        :class="{ primary: scope === 'pending' }"
        type="button"
        @click="switchScope('pending')"
      >
        待监护视图（{{ summary.pending }}）
      </button>
      <button
        class="btn"
        :class="{ primary: scope === 'all' }"
        type="button"
        @click="switchScope('all')"
      >
        全部台账（{{ summary.all }}）
      </button>
      <span class="scope-tip">完工项目不再进入待监护视图，可在全部台账中回看。</span>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>项目检索</span>
        <input v-model="keyword" placeholder="按项目编号 / 名称 / 外部单位检索" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetKeyword">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>项目状态</th>
          <th>监护明细</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)" :class="{ 'row-warn': !row['已交底'] }">
          <td>{{ row['项目编号'] ?? '—' }}</td>
          <td>
            {{ row['项目名称'] ?? '—' }}
            <span v-if="!row['已交底']" class="tag tag-warn">未交底</span>
          </td>
          <td>{{ row['外部单位'] ?? '—' }}</td>
          <td>{{ row['涉及管段'] ?? '—' }}</td>
          <td>
            <template v-if="row['交底时间']">{{ row['交底时间'] }}</template>
            <span v-else class="warn-text">尚未交底</span>
          </td>
          <td>{{ row['监护人'] || '—' }}</td>
          <td>
            <strong>{{ row['监护记录条数'] }}</strong> 条
            <span v-if="row['未闭环违章数']" class="warn-text">（{{ row['未闭环违章数'] }} 条违章未闭环）</span>
          </td>
          <td>
            <span :class="row['status'] === '已完工' ? 'tag tag-done' : 'tag tag-active'">{{ row['status'] }}</span>
          </td>
          <td>
            <RouterLink class="link" :to="`/guard/${row.id}`">查看旁站监护明细</RouterLink>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 2" class="empty-state">{{ emptyText }}</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>
        <template v-if="scope === 'pending'">待监护视图共 {{ summary.pending }} 个在建项目，与运营概览「在建监护数」一致</template>
        <template v-else>全部台账共 {{ summary.all }} 个项目（含已完工）</template>
        <template v-if="keyword.trim() && total !== (scope === 'pending' ? summary.pending : summary.all)">，本次检索命中 {{ total }} 个</template>
      </span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchJson } from '@/api/client'

type ProjectRow = {
  id: number
  status: string
  已交底: boolean
  项目编号: string
  项目名称: string
  外部单位: string
  涉及管段: string
  交底时间: string | null
  监护人: string
  监护记录条数: number
  未闭环违章数: number
}

type PagePayload = { items: ProjectRow[]; total: number }

const ENDPOINT = '/api/guard'
const columns = ['项目编号', '项目名称', '外部单位', '涉及管段', '交底时间', '监护人', '监护记录条数']

const rows = ref<ProjectRow[]>([])
const total = ref(0)
const scope = ref<'pending' | 'all'>('pending')
const keyword = ref('')
const errorMessage = ref('')

const summary = ref({ pending: 0, all: 0 })

const stats = computed(() => [
  { label: '在建监护项目', value: summary.value.pending },
  { label: '未交底项目', value: rows.value.filter((row) => !row['已交底']).length },
  { label: '未闭环违章记录', value: rows.value.reduce((sum, row) => sum + Number(row['未闭环违章数'] || 0), 0) },
  { label: '监护记录累计', value: rows.value.reduce((sum, row) => sum + Number(row['监护记录条数'] || 0), 0) },
])

const emptyText = computed(() =>
  scope.value === 'pending'
    ? '暂无待监护的施工项目：当前没有在建的第三方施工需要交底与旁站监护'
    : '暂无施工监护台账记录：外部单位报送施工项目后将在这里集中呈现',
)

function switchScope(next: 'pending' | 'all') {
  scope.value = next
  void reload()
}

function resetKeyword() {
  keyword.value = ''
  void reload()
}

async function reload() {
  errorMessage.value = ''
  try {
    const query = new URLSearchParams({ scope: scope.value })
    if (keyword.value.trim()) {
      query.set('keyword', keyword.value.trim())
    }
    const payload = await fetchJson<PagePayload>(`${ENDPOINT}?${query.toString()}`)
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    // 拉两个口径的总数用于视图切换标签，概览卡片与 pending 总数同口径。
    const [pendingPage, allPage] = await Promise.all([
      fetchJson<PagePayload>(`${ENDPOINT}?scope=pending&size=1`),
      fetchJson<PagePayload>(`${ENDPOINT}?scope=all&size=1`),
    ])
    summary.value = { pending: pendingPage.total ?? 0, all: allPage.total ?? 0 }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '施工监护台账读取失败'
  }
}

onMounted(reload)
</script>
