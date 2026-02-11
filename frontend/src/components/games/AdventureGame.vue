<template>
  <div class="adventure-game">
    <!-- 状态栏 -->
    <div class="status-bar">
      <div class="hp-bar">
        <div class="hp-fill" :style="{ width: hpPct + '%', background: hpColor }"></div>
        <span class="hp-text">HP {{ state.hp }}/{{ state.max_hp }}</span>
      </div>
      <div class="stats">
        <span>🗡️{{ state.attack }}</span>
        <span>🛡️{{ state.defense }}</span>
        <span>🧪{{ state.potions }}</span>
        <span>📍{{ state.floor }}F</span>
        <span>⭐{{ state.exp_earned }}</span>
      </div>
      <!-- 已获得的增益 -->
      <div v-if="state.buffs && state.buffs.length" class="buffs-bar">
        <span v-for="(b, i) in state.buffs" :key="i" class="buff-tag">{{ b }}</span>
      </div>
    </div>

    <!-- 战斗日志 -->
    <div class="log-area" ref="logRef">
      <div v-for="(msg, i) in state.log" :key="i" class="log-line">{{ msg }}</div>
    </div>

    <!-- 遭遇面板 -->
    <div v-if="state.encounter && !state.game_over" class="encounter-panel">
      <!-- 怪物/Boss -->
      <template v-if="enc.type === 'monster' || enc.type === 'boss'">
        <div class="encounter-info">
          <span class="enc-icon">{{ enc.type === 'boss' ? '🐉' : '👾' }}</span>
          <span class="enc-name">{{ enc.name }}</span>
          <div class="monster-hp">
            <div class="monster-hp-fill" :style="{ width: monsterHpPct + '%' }"></div>
            <span>{{ enc.monster_hp }}/{{ enc.monster_max_hp }}</span>
          </div>
        </div>
        <div v-if="!state.encounter_resolved" class="action-btns">
          <button class="btn fight" @click="doAction('fight')">⚔️ 战斗</button>
          <button class="btn potion" @click="doAction('use_potion')" :disabled="state.potions <= 0">🧪 药水</button>
          <button class="btn flee" @click="doAction('flee')">🏃 逃跑</button>
        </div>
      </template>

      <!-- 宝箱 -->
      <template v-else-if="enc.type === 'chest'">
        <div class="encounter-info">
          <span class="enc-icon">🎁</span>
          <span class="enc-name">发现宝箱！</span>
        </div>
        <div v-if="!state.encounter_resolved" class="action-btns">
          <button class="btn chest" @click="doAction('open')">🎁 打开宝箱</button>
        </div>
      </template>

      <!-- 陷阱 -->
      <template v-else-if="enc.type === 'trap'">
        <div class="encounter-info">
          <span class="enc-icon">⚠️</span>
          <span class="enc-name">发现陷阱！</span>
        </div>
        <div v-if="!state.encounter_resolved" class="action-btns">
          <button class="btn disarm" @click="doAction('disarm')">🔧 拆除 (60%)</button>
          <button class="btn bypass" @click="doAction('bypass')">🚶 绕过</button>
        </div>
      </template>

      <!-- 商店 -->
      <template v-else-if="enc.type === 'shop'">
        <div class="encounter-info">
          <span class="enc-icon">🏪</span>
          <span class="enc-name">发现商店</span>
        </div>
        <div v-if="!state.encounter_resolved" class="action-btns shop-btns">
          <button class="btn shop" @click="doAction('buy_potion')" :disabled="state.exp_earned < 8">
            🧪 药水 (8EXP)
          </button>
          <button class="btn shop" @click="doAction('buy_shield')" :disabled="state.exp_earned < 12">
            🛡️ 护盾 (12EXP)
          </button>
          <button class="btn shop" @click="doAction('buy_sword')" :disabled="state.exp_earned < 15">
            ⚔️ 短剑 (15EXP)
          </button>
          <button class="btn skip" @click="doAction('skip')">🚶 离开</button>
        </div>
      </template>

      <!-- 祝福 -->
      <template v-else-if="enc.type === 'blessing'">
        <div class="encounter-info">
          <span class="enc-icon">✨</span>
          <span class="enc-name">{{ enc.name }}</span>
        </div>
        <div class="blessing-hint">选择一个祝福增益：</div>
        <div v-if="!state.encounter_resolved" class="blessing-choices">
          <button
            v-for="choice in (enc.choices || [])"
            :key="choice.id"
            class="blessing-choice"
            @click="chooseBlessing(choice.id)"
          >
            <span class="blessing-name">{{ choice.name }}</span>
            <span class="blessing-desc">{{ choice.desc }}</span>
          </button>
        </div>
      </template>

      <!-- 已解决 → 下一层 -->
      <div v-if="state.encounter_resolved && !state.game_over" class="action-btns">
        <button class="btn next" @click="doAction('next_floor')">
          {{ state.floor >= state.max_floor ? '🏆 完成探险' : '📍 进入下一层' }}
        </button>
      </div>
    </div>

    <!-- 结果 -->
    <div v-if="state.game_over" class="game-result" :class="resultClass">
      <div class="result-title">{{ resultTitle }}</div>
      <div class="result-detail">通过 {{ state.floors_cleared }}/{{ state.max_floor }} 层</div>
      <div v-if="state.exp_earned > 0 && !state.abandoned" class="result-exp">获得 {{ state.exp_earned }} EXP</div>
      <div v-else class="result-exp lost">未获得经验</div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { adventureSound } from '../../utils/gameSound'

const props = defineProps<{ state: any }>()
const emit = defineEmits<{ (e: 'action', action: any): void }>()
const logRef = ref<HTMLDivElement>()
const showAbandonConfirm = ref(false)

const enc = computed(() => props.state.encounter || {})
const hpPct = computed(() => (props.state.hp / props.state.max_hp) * 100)
const hpColor = computed(() => hpPct.value > 60 ? '#4caf50' : hpPct.value > 30 ? '#ff9800' : '#f44336')
const monsterHpPct = computed(() => {
  const e = enc.value
  return e.monster_max_hp ? (e.monster_hp / e.monster_max_hp) * 100 : 0
})

// 结果展示
const resultClass = computed(() => {
  if (props.state?.abandoned) return 'lose'
  return props.state?.floors_cleared >= props.state?.max_floor ? 'win' : 'lose'
})

const resultTitle = computed(() => {
  if (props.state?.abandoned) return '🏳️ 已放弃'
  if (props.state?.floors_cleared >= props.state?.max_floor) return '🏆 全部通关！'
  if (props.state?.hp <= 0) return '💀 探险失败'
  return '探险结束'
})

watch(() => props.state.log?.length, () => {
  nextTick(() => {
    if (logRef.value) logRef.value.scrollTop = logRef.value.scrollHeight
  })
})

// 监听HP减少播放受伤音效
watch(() => props.state?.hp, (newHp, oldHp) => {
  if (oldHp !== undefined && newHp < oldHp) {
    adventureSound.hurt()
  }
})

function doAction(act: string) {
  // 播放音效
  if (act === 'fight') adventureSound.attack()
  else if (act === 'next_floor') adventureSound.nextFloor()
  else if (act === 'buy_potion' || act === 'buy_shield' || act === 'buy_sword') adventureSound.shop()
  else if (act === 'open') adventureSound.chest()
  emit('action', { action: act })
}

function chooseBlessing(blessingId: string) {
  adventureSound.buff()
  emit('action', { action: 'choose_blessing', blessing_id: blessingId })
}

function doAbandon() {
  showAbandonConfirm.value = false
  emit('action', { action: 'abandon' })
}
</script>

<style scoped>
.adventure-game {
  padding: 8px;
  position: relative;
}
.status-bar {
  margin-bottom: 8px;
}
.hp-bar {
  position: relative;
  height: 22px;
  background: var(--theme-bg-secondary, #eee);
  border-radius: 11px;
  overflow: hidden;
  margin-bottom: 6px;
}
.hp-fill {
  height: 100%;
  border-radius: 11px;
  transition: width 0.3s, background 0.3s;
}
.hp-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  font-weight: bold;
  color: var(--theme-text-primary, #333);
  text-shadow: 0 0 3px var(--theme-bg-card, #fff);
}
.stats {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}
.buffs-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: center;
  margin-top: 6px;
}
.buff-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 10px;
  background: var(--theme-success-bg, linear-gradient(135deg, #e8f5e9, #fff8e1));
  border: 1px solid var(--theme-success-light, #c8e6c9);
  color: var(--theme-success, #2e7d32);
  white-space: nowrap;
}
.abandon-btn-inline {
  padding: 4px 8px;
  border: 1px solid var(--theme-border, #ddd);
  border-radius: 6px;
  background: var(--theme-bg-card, #fff);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  margin-left: 4px;
}
.abandon-btn-inline:hover {
  background: var(--theme-error-bg, #ffebee);
  border-color: var(--theme-error-light, #ef9a9a);
}
.log-area {
  height: 120px;
  overflow-y: auto;
  background: var(--theme-bg-secondary, #f9f9f9);
  border-radius: 8px;
  padding: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  line-height: 1.6;
}
.log-line {
  color: var(--theme-text-secondary, #555);
}
.encounter-panel {
  background: var(--theme-bg-card, #fff);
  border-radius: 8px;
  padding: 12px;
  border: 1px solid var(--theme-border-light, #eee);
}
.encounter-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.enc-icon { font-size: 28px; }
.enc-name { font-size: 16px; font-weight: bold; }
.monster-hp {
  position: relative;
  flex: 1;
  min-width: 80px;
  height: 16px;
  background: #ffcdd2;
  border-radius: 8px;
  overflow: hidden;
}
.monster-hp-fill {
  height: 100%;
  background: #e53935;
  border-radius: 8px;
  transition: width 0.3s;
}
.monster-hp span {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 10px;
  color: var(--theme-text-primary, #333);
  font-weight: bold;
}
.action-btns {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.btn {
  flex: 1;
  min-width: 70px;
  padding: 8px 4px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: bold;
  cursor: pointer;
  color: white;
}
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn.fight { background: #e53935; }
.btn.potion { background: #43a047; }
.btn.flee { background: #757575; }
.btn.chest { background: #ff9800; }
.btn.disarm { background: #ff5722; }
.btn.bypass { background: #9e9e9e; }
.btn.shop { background: #1565c0; }
.btn.skip { background: #757575; }
.btn.next { background: linear-gradient(135deg, #667eea, #764ba2); }
.shop-btns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

/* 祝福选择 */
.blessing-hint {
  font-size: 13px;
  color: var(--theme-text-secondary, #666);
  margin-bottom: 8px;
  text-align: center;
}
.blessing-choices {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.blessing-choice {
  display: flex;
  flex-direction: column;
  padding: 10px 14px;
  border: 2px solid var(--theme-border, #e8e8e8);
  border-radius: 10px;
  background: var(--theme-bg-secondary, linear-gradient(135deg, #fafafa, #f5f0ff));
  cursor: pointer;
  transition: all 0.2s;
}
.blessing-choice:hover {
  border-color: var(--theme-purple, #9c7cf4);
  background: var(--theme-purple-light, linear-gradient(135deg, #f3edff, #e8e0ff));
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(103, 58, 183, 0.15);
}
.blessing-name {
  font-size: 15px;
  font-weight: bold;
  color: var(--theme-purple, #5e35b1);
}
.blessing-desc {
  font-size: 12px;
  color: var(--theme-text-tertiary, #888);
  margin-top: 2px;
}

/* 结果 */
.game-result {
  text-align: center;
  padding: 12px;
  border-radius: 8px;
  margin-top: 8px;
}
.game-result.win {
  background: var(--theme-success-bg, linear-gradient(135deg, #e8f5e9, #c8e6c9));
}
.game-result.lose {
  background: var(--theme-error-bg, linear-gradient(135deg, #ffebee, #ffcdd2));
}
.result-title {
  font-size: 18px;
  font-weight: bold;
}
.win .result-title { color: var(--theme-success, #2e7d32); }
.lose .result-title { color: var(--theme-error, #c62828); }
.result-detail {
  font-size: 14px;
  margin-top: 4px;
}
.win .result-detail { color: var(--theme-success, #388e3c); }
.lose .result-detail { color: var(--theme-error-light, #e57373); }
.result-exp {
  font-size: 14px;
  color: var(--theme-success, #388e3c);
  margin-top: 4px;
}
.result-exp.lost {
  color: var(--theme-text-tertiary, #999);
}

/* 确认弹窗 */
.confirm-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  z-index: 100;
}
.confirm-dialog {
  background: var(--theme-bg-card, white);
  border-radius: 12px;
  padding: 20px;
  max-width: 280px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}
.confirm-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 12px;
}
.confirm-message {
  font-size: 14px;
  color: var(--theme-text-secondary, #666);
  margin-bottom: 20px;
  line-height: 1.5;
}
.confirm-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
.confirm-btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}
.confirm-btn.cancel {
  background: var(--theme-bg-secondary, #f5f5f5);
  color: var(--theme-text-secondary, #666);
}
.confirm-btn.cancel:hover {
  background: var(--theme-border, #e0e0e0);
}
.confirm-btn.confirm {
  background: #ef5350;
  color: white;
}
.confirm-btn.confirm:hover {
  background: #e53935;
}
</style>