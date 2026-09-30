<template>
  <section class="page" data-module="guard-detail" v-if="detail">
    <header class="page-head">
      <div>
        <button class="btn ghost" type="button" @click="goBack">← 返回监护台账</button>
        <h2 class="detail-title">
          {{ detail['项目编号'] }} · {{ detail['项目名称'] }}
          <span class="tag" :class="detail['项目状态'] === '在建' ? 'tag-active' : 'tag-done'">{{ detail['项目状态'] }}</span>
        </h2>
        <p class="page-desc">
          外部单位：{{ detail['外部单位'] }} ｜ 涉及管段：{{ detail['涉及管段'] }} ｜ 登记日期：{{ detail['登记日期'] }}
          <template v-if="detail['完工日期']"> ｜ 完工日期：{{ detail['完工日期'] }}</template>
        </p>
      </div>
      <div class="page-actions">
        <button
          class="btn primary"
          type="button"
          :disabled="detail['项目状态'] === '已完工'"
          @click="completeProject"
        >
          标注完工
        </button>
      </div>
    </header>

    <div class="stat-row">
      <article class="stat-card">
        <span class="stat-label">监护记录条数（同步台账视图）</span>
        <strong class="stat-value">{{ detail['监护记录条数'] }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">未闭环违章</span>
        <strong class="stat-value" :class="{ 'text-danger': detail['未闭环违章数'] }">{{ detail['未闭环违章数'] }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">交底状态</span>
        <strong class="stat-value">{{ detail['是否已交底'] ? '已交底' : '未交底' }}</strong>
      </article>
    </div>

    <div class="panel">
      <div class="panel-head">
        <h3>施工交底（同一项目重复报送仅保留最新一版）</h3>
        <button class="btn" type="button" @click="showBriefingForm = !showBriefingForm">
          {{ detail['交底记录'] ? '重新报送交底' : '报送交底' }}
        </button>
      </div>
      <div v-if="detail['交底记录']" class="briefing-card">
        <p><strong>交底时间：</strong>{{ detail['交底记录']['交底时间'] }} ｜ <strong>交底地点：</strong>{{ detail['交底记录']['交底地点'] || '—' }}</p>
        <p><strong>交底人员：</strong>{{ detail['交底记录']['交底人员'] }} ｜ <strong>指定监护人：</strong>{{ detail['交底记录']['监护人'] }}</p>
        <p><strong>交底内容：</strong>{{ detail['交底记录']['交底内容'] || '—' }}</p>
      </div>
      <div v-else class="empty-block">
    该项目还没有交底记录，请先组织施工交底；交底完成前不能标注完工。
      </div>
      <form v-if="showBriefingForm" class="inline-form" @submit.prevent="submitBriefing">
        <label class="filter-item"><span>交底时间</span><input v-model="briefingForm['交底时间']" placeholder="如 2026-09-30 09:00" /></label>
        <label class="filter-item"><span>交底地点</span><input v-model="briefingForm['交底地点']" placeholder="交底地点" /></label>
        <label class="filter-item"><span>交底人员</span><input v-model="briefingForm['交底人员']" placeholder="交底人员" /></label>
        <label class="filter-item"><span>监护人</span><input v-model="briefingForm['监护人']" placeholder="现场监护人" /></label>
        <label class="filter-item filter-wide"><span>交底内容</span><textarea v-model="briefingForm['交底内容']" rows="2" placeholder="保护范围、禁止事项、应急要求等"></textarea></label>
        <div class="form-actions">
          <button class="btn ghost" type="button" @click="showBriefingForm = false">取消</button>
          <button class="btn primary" type="submit">保存最新交底</button>
        </div>
      </form>
    </div>

    <div class="panel">
      <div class="panel-head">
        <h3>旁站监护明细（{{ detail['监护记录条数'] }} 条）</h3>
        <button class="btn" type="button" @click="showRecordForm = !showRecordForm">补录监护记录</button>
      </div>
      <form v-if="showRecordForm" class="inline-form" @submit.prevent="submitRecord">
        <label class="filter-item"><span>监护时间</span><input v-model="recordForm['监护时间']" placeholder="如 2026-09-30 14:00" /></label>
        <label class="filter-item"><span>监护地点</span><input v-model="recordForm['监护地点']" placeholder="作业点位" /></label>
        <label class="filter-item"><span>监护人</span><input v-model="recordForm['监护人']" placeholder="旁站监护人" /></label>
        <label class="filter-item">
          <span>监护结论</span>
          <select v-model="recordForm['监护结论']">
            <option value="正常">正常</option>
            <option value="发现违章">发现违章</option>
          </select>
        </label>
        <label class="filter-item filter-wide"><span>监护内容</span><textarea v-model="recordForm['监护内容']" rows="2" placeholder="作业内容、发现问题、处置要求"></textarea></label>
        <div class="form-actions">
          <button class="btn ghost" type="button" @click="showRecordForm = false">取消</button>
          <button class="btn primary" type="submit">保存并同步台账条数</button>
        </div>
      </form>

      <table class="data-table">
        <thead>
          <tr><th>监护时间</th><th>监护地点</th><th>监护人</th><th>监护内容</th><th>结论</th><th>闭环状态</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="record in detail['监护记录']" :key="String(record.id)" :class="{ 'row-warning': record['监护结论'] === '发现违章' && !record['是否闭环'] }">
            <td>{{ record['监护时间'] }}</td>
            <td>{{ record['监护地点'] || '—' }}</td>
            <td>{{ record['监护人'] }}</td>
            <td class="content-cell">{{ record['监护内容'] }}</td>
            <td><span class="tag" :class="record['监护结论'] === '发现违章' ? 'tag-danger' : 'tag-ok'">{{ record['监护结论'] }}</span></td>
            <td>
              <span v-if="record['监护结论'] !== '发现违章'">—</span>
              <span v-else-if="record['是否闭环']" class="tag tag-ok">已闭环</span>
              <span v-else class="tag tag-danger">未闭环</span>
            </td>
            <td class="row-actions">
              <button
                v-if="record['监护结论'] === '发现违章' && !record['是否闭环']"
                class="link"
                type="button"
                @click="closeRecord(Number(record.id))"
              >
                闭环违章
              </button>
            </td>
          </tr>
          <tr v-if="!detail['监护记录'].length">
            <td colspan="7" class="empty-state">该项目暂无旁站监护记录，可点击「补录监护记录」登记第一次旁站。</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="page-foot">
      <span v-if="message" :class="messageOk ? '' : 'error-text'">{{ message }}</span>
    </footer>
  </section>
  <section v-else class="page">
    <p class="empty-state">施工项目加载中或不存在，<RouterLink class="link" to="/guard">返回监护台账</RouterLink>。</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { request } from '@/api/client'

const props = defineProps<{ id: string }>()
const router = useRouter()

type RecordRow = Record<string, string | number | boolean | null>
type Detail = Record<string, any> & { 监护记录: RecordRow[] }

const detail = ref<Detail | null>(null)
const message = ref('')
const messageOk = ref(true)
const showBriefingForm = ref(false)
const showRecordForm = ref(false)

function emptyBriefing() {
  return { 交底时间: '', 交底地点: '', 交底人员: '', 监护人: '', 交底内容: '' }
}
function emptyRecord() {
  return { 监护时间: '', 监护地点: '', 监护人: '', 监护结论: '正常', 监护内容: '' }
}
const briefingForm = reactive(emptyBriefing())
const recordForm = reactive(emptyRecord())

function notify(text: string, ok = true) {
  message.value = text
  messageOk.value = ok
}

function goBack() {
  void router.push({ name: 'guard' })
}

async function load() {
  try {
    const response = await request(`/api/guard/projects/${props.id}`)
    if (!response.ok) throw new Error('项目明细读取失败')
    detail.value = await response.json()
  } catch (error) {
    notify(error instanceof Error ? error.message : '项目明细读取失败', false)
  }
}

async function postAction(path: string, body?: unknown) {
  const response = await request(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok || !payload?.ok) {
    throw new Error(payload?.message ? String(payload.message) : '操作未生效，请稍后重试')
  }
  return String(payload.message ?? '操作成功')
}

async function submitBriefing() {
  try {
    const text = await postAction(`/api/guard/projects/${props.id}/briefing`, { values: { ...briefingForm } })
    notify(text, true)
    showBriefingForm.value = false
    Object.assign(briefingForm, emptyBriefing())
    await load()
  } catch (error) {
    notify(error instanceof Error ? error.message : '交底报送失败', false)
  }
}

async function submitRecord() {
  try {
    const text = await postAction(`/api/guard/projects/${props.id}/records`, { values: { ...recordForm } })
    notify(text, true)
    showRecordForm.value = false
    Object.assign(recordForm, emptyRecord())
    await load()
  } catch (error) {
    notify(error instanceof Error ? error.message : '监护记录补录失败', false)
  }
}

async function closeRecord(recordId: number) {
  try {
    notify(await postAction(`/api/guard/records/${recordId}/close`), true)
    await load()
  } catch (error) {
    notify(error instanceof Error ? error.message : '违章闭环失败', false)
  }
}

async function completeProject() {
  try {
    notify(await postAction(`/api/guard/projects/${props.id}/complete`), true)
    await load()
  } catch (error) {
    notify(error instanceof Error ? error.message : '完工标注失败', false)
  }
}

onMounted(load)
</script>

<style scoped>
.detail-title { margin: 8px 0 4px; font-size: 18px; }
.text-danger { color: #b42318; }
.panel { background: #fff; border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; margin-bottom: 14px; }
.panel-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.panel-head h3 { margin: 0; font-size: 15px; }
.briefing-card p { margin: 4px 0; font-size: 13px; }
.empty-block { border: 1px dashed #fda29b; background: #fef3f2; color: #b42318; border-radius: 6px; padding: 10px 12px; font-size: 13px; }
.inline-form { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; border-top: 1px dashed var(--border); padding-top: 10px; margin-top: 10px; }
.inline-form .filter-item span { display: block; font-size: 12px; color: var(--muted); }
.inline-form input, .inline-form select, .inline-form textarea { min-width: 180px; padding: 5px 8px; border: 1px solid var(--border); border-radius: 6px; font: inherit; }
.filter-wide { flex-basis: 100%; }
.filter-wide textarea { width: 100%; }
.form-actions { flex-basis: 100%; display: flex; justify-content: flex-end; gap: 8px; }
.content-cell { max-width: 320px; }
.row-warning td { background: #fff7ed; }
.tag { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 12px; border: 1px solid var(--border); }
.tag-danger { color: #b42318; border-color: #fda29b; background: #fef3f2; }
.tag-ok { color: #027a48; border-color: #6ce9a6; background: #ecfdf3; }
.tag-active { color: #b54708; border-color: #fec84b; background: #fffaeb; }
.tag-done { color: #027a48; border-color: #6ce9a6; background: #ecfdf3; }
</style>
