<template>
  <div class="token-dashboard" :class="{ 'has-update': pulse, 'is-loading': !projectId && !simulationId }">
    <div class="stats-icon">
      <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>
    
    <div class="stats-wrapper">
      <div class="stats-content">
        <span class="label">本轮累计</span>
        <div class="value-container">
          <span class="value">{{ formattedTokens(displayStats.total_tokens) }}</span>
          <span class="unit">tkns</span>
        </div>
      </div>
      
      <!-- 项目全局累计 (仅在 Simulation 模式或 Step 2+ 显示) -->
      <div v-if="showTotal" class="stats-divider"></div>
      
      <div v-if="showTotal" class="stats-content total-mode">
        <span class="label">项目累计</span>
        <div class="value-container">
          <span class="value">{{ formattedTokens(totalStats.total_tokens) }}</span>
          <span class="unit">tkns</span>
        </div>
      </div>
    </div>

    <!-- 悬浮详情 -->
    <div class="token-tooltip">
      <div class="tool-title">消耗详情明细</div>
      
      <div class="tool-section">
        <div class="section-label">本轮累计</div>
        <div class="tool-row">
          <span>Prompt:</span>
          <span class="mono">{{ displayStats.prompt_tokens?.toLocaleString() }}</span>
        </div>
        <div class="tool-row">
          <span>Completion:</span>
          <span class="mono">{{ displayStats.completion_tokens?.toLocaleString() }}</span>
        </div>
        <div class="tool-row total">
          <span>Calls:</span>
          <span>{{ displayStats.call_count }}</span>
        </div>
      </div>

      <div v-if="showTotal" class="divider"></div>

      <div v-if="showTotal" class="tool-section">
        <div class="section-label">项目全链路累计</div>
        <div class="tool-row">
          <span>Prompt:</span>
          <span class="mono">{{ totalStats.prompt_tokens?.toLocaleString() }}</span>
        </div>
        <div class="tool-row">
          <span>Completion:</span>
          <span class="mono">{{ totalStats.completion_tokens?.toLocaleString() }}</span>
        </div>
        <div class="tool-row total">
          <span>Calls:</span>
          <span>{{ totalStats.call_count }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { getSimulationUsage } from '../api/simulation'
import { getProjectUsage } from '../api/graph'

const props = defineProps({
  simulationId: {
    type: String,
    required: false,
    default: null
  },
  projectId: {
    type: String,
    required: false,
    default: null
  },
  step: {
    type: String,
    required: false,
    default: null
  }
})

const stats = ref({
  prompt_tokens: 0,
  completion_tokens: 0,
  total_tokens: 0,
  call_count: 0
})

const totalStats = ref({
  prompt_tokens: 0,
  completion_tokens: 0,
  total_tokens: 0,
  call_count: 0
})

const pulse = ref(false)
let timer = null

// 直接显示后端返回的数据（后端已根据 step 完成分账逻辑）
const displayStats = computed(() => {
  return {
    prompt_tokens: stats.value.prompt_tokens || 0,
    completion_tokens: stats.value.completion_tokens || 0,
    total_tokens: stats.value.total_tokens || 0,
    call_count: stats.value.call_count || 0
  }
})

// 是否显示项目累计
const showTotal = computed(() => {
  // 如果是模拟模式，肯定显示总计
  if (props.simulationId) return true
  // 如果是项目模式，只有总计多于当前值（意味着有其他环节损耗）时显示，或者单纯为了保持风格一致
  return props.projectId && props.projectId !== 'new'
})

const formattedTokens = (val) => {
  const total = val || 0
  if (total >= 1000000) return (total / 1000000).toFixed(2) + 'M'
  if (total >= 1000) return (total / 1000).toFixed(1) + 'K'
  return total.toLocaleString()
}

// 改进：增加对 new 项目的处理和更鲁棒的显示逻辑
const fetchStats = async () => {
  if (!props.projectId && !props.simulationId) return;
  if (props.projectId === 'new') return;
  
  try {
    // 物理对齐：始终拉取一次项目级的全量数据作为“底座”
    const projectRes = await getProjectUsage(props.projectId)
    if (projectRes && projectRes.success) {
      totalStats.value = projectRes.total || projectRes.data || totalStats.value
    }

    if (props.simulationId) {
      // 模拟级统计 (Step 3, 4, 5)
      const res = await getSimulationUsage(props.simulationId, props.step)
      if (res && res.success) {
        const newData = res.data || {}
        if (newData.total_tokens !== stats.value.total_tokens) {
          triggerPulse()
        }
        // 如果本环节数据为0，但总数据不为0且在Step 3+，尝试从全链路中寻找该仿真
        stats.value = newData
        // 自动对齐总数
        if (res.total) totalStats.value = res.total
      }
    } else {
      // Step 1/2 项目级直接显示统计
      stats.value = projectRes.data || stats.value
    }
    } catch (err) {
    if (err.response?.status !== 404) {
      console.warn('TokenDashboard 物理同步尝试中...', err.message)
    }
  }
}

// 提高轮询频率至 2s，增强实时感
const PULSE_INTERVAL = 2000 

const triggerPulse = () => {
  pulse.value = true
  setTimeout(() => {
    pulse.value = false
  }, 1000)
}

onMounted(() => {
  fetchStats()
  timer = setInterval(fetchStats, PULSE_INTERVAL) // 2s 物理轮询
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

watch(() => [props.simulationId, props.projectId], ([newSim, newProj], [oldSim, oldProj]) => {
  if (newSim !== oldSim || newProj !== oldProj) {
    if (newProj === 'new') {
       stats.value = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, call_count: 0 }
       totalStats.value = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, call_count: 0 }
    }
    fetchStats()
  }
})
</script>

<style scoped>
.token-dashboard {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 16px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  cursor: help;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}

.token-dashboard:hover {
  background: #FFF;
  border-color: rgba(33, 150, 243, 0.3);
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(33, 150, 243, 0.08);
}

.stats-icon {
  width: 18px;
  height: 18px;
  color: #2196F3;
  flex-shrink: 0;
}

.stats-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stats-divider {
  width: 1px;
  height: 20px;
  background: rgba(0, 0, 0, 0.06);
}

.stats-content {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.total-mode .value {
  color: #666;
}

.label {
  font-size: 9px;
  font-weight: 800;
  text-transform: uppercase;
  color: #AAA;
  letter-spacing: 0.8px;
  margin-bottom: 1px;
}

.value-container {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.value {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  font-size: 14px;
  color: #000;
  transition: color 0.3s;
}

.unit {
  font-size: 9px;
  font-weight: 700;
  color: #BBB;
  text-transform: lowercase;
}

/* 脉冲动画 */
.has-update {
  box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.15);
  border-color: rgba(33, 150, 243, 0.4);
}

.has-update .value {
  color: #2196F3;
}

/* Tooltip */
.token-tooltip {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  width: 200px;
  background: #FFF;
  border: 1px solid #EEE;
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 12px 30px rgba(0,0,0,0.12);
  opacity: 0;
  visibility: hidden;
  transform: translateY(8px);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1000;
}

.token-dashboard:hover .token-tooltip {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.tool-title {
  font-size: 11px;
  font-weight: 900;
  color: #000;
  text-transform: uppercase;
  margin-bottom: 12px;
  letter-spacing: 1px;
}

.tool-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-label {
  font-size: 10px;
  font-weight: 800;
  color: #2196F3;
  margin-bottom: 4px;
  background: rgba(33, 150, 243, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  width: fit-content;
}

.tool-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #777;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  color: #333;
}

.divider {
  height: 1px;
  background: #F0F0F0;
  margin: 10px 0;
}

.total {
  margin-top: 2px;
  font-weight: 800;
  color: #000;
  border-top: 1px dashed #EEE;
  padding-top: 4px;
}
</style>
