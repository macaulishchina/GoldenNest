<template>
  <div class="adventure-game" @click="clearSelect">
    <!-- 状态栏 -->
    <div class="status-bar">
      <div class="hp-bar">
        <div class="hp-fill" :style="{ width: hpPct + '%', background: hpColor }"></div>
        <span class="hp-text">HP {{ state.hp }}/{{ state.max_hp }}</span>
      </div>
      <div class="stats-row" @click.stop="showStatDetail = !showStatDetail">
        <span>🗡️{{ totalAtk }}</span>
        <span>🛡️{{ totalDef }}</span>
        <span v-if="totalLifesteal > 0">🧛{{ totalLifesteal }}%</span>
        <span v-if="totalCrit > 0">🎯{{ totalCrit }}%</span>
        <span v-if="totalCritDmg > 180">💥{{ totalCritDmg }}%</span>
        <span>📍{{ state.floor }}F{{ state.endless ? '' : `/${state.max_floor}` }}</span>
        <span>⭐{{ state.exp_earned }}</span>
      </div>
      <!-- 属性详情面板 -->
      <div v-if="showStatDetail" class="stat-detail-panel" @click.stop>
        <div class="sdp-title">📊 属性详情 <span class="sdp-close" @click="showStatDetail = false">✕</span></div>
        <div class="sdp-section">👤 自身属性（祝福）</div>
        <div class="sdp-row"><span>🗡️ 攻击</span><b>{{ state.attack || 0 }}</b><span class="sdp-desc">每回合对怪物造成的基础伤害</span></div>
        <div class="sdp-row"><span>🛡️ 防御</span><b>{{ state.defense || 0 }}</b><span class="sdp-desc">减少受到的伤害（怪物攻击-防御）</span></div>
        <div class="sdp-row"><span>🎯 暴击率</span><b>{{ state.crit_chance || 0 }}%</b><span class="sdp-desc">攻击时触发暴击的概率</span></div>
        <div class="sdp-row"><span>💥 暴击伤害</span><b>{{ state.crit_damage || 180 }}%</b><span class="sdp-desc">暴击时伤害倍率（基础180%）</span></div>
        <div class="sdp-row"><span>🧛 吸血</span><b>{{ state.lifesteal || 0 }}%</b><span class="sdp-desc">攻击伤害的一定比例转化为HP恢复</span></div>
        <div class="sdp-row"><span>❤️ 最大HP</span><b>{{ state.max_hp }}</b><span class="sdp-desc">生命值上限</span></div>
        <template v-if="bpStats">
          <div class="sdp-section">🎒 背包加成</div>
          <div v-if="bpStats.atk" class="sdp-row"><span>🗡️ 攻击</span><b>+{{ bpStats.atk }}</b></div>
          <div v-if="bpStats.def" class="sdp-row"><span>🛡️ 防御</span><b>+{{ bpStats.def }}</b></div>
          <div v-if="bpStats.crit" class="sdp-row"><span>🎯 暴击率</span><b>+{{ bpStats.crit }}%</b></div>
          <div v-if="bpStats.crit_damage" class="sdp-row"><span>💥 暴击伤害</span><b>+{{ bpStats.crit_damage }}%</b></div>
          <div v-if="bpStats.lifesteal" class="sdp-row"><span>🧛 吸血</span><b>+{{ bpStats.lifesteal }}%</b></div>
          <div v-if="bpStats.max_hp" class="sdp-row"><span>❤️ 最大HP</span><b>+{{ bpStats.max_hp }}</b></div>
          <div v-if="bpStats.exp_bonus" class="sdp-row"><span>📖 经验加成</span><b>+{{ bpStats.exp_bonus }}%</b></div>
        </template>
        <div class="sdp-section">📈 合计</div>
        <div class="sdp-row total"><span>🗡️ 总攻击</span><b>{{ totalAtk }}</b></div>
        <div class="sdp-row total"><span>🛡️ 总防御</span><b>{{ totalDef }}</b></div>
        <div class="sdp-row total"><span>🎯 总暴击</span><b>{{ totalCrit }}%</b></div>
        <div class="sdp-row total"><span>💥 总暴伤</span><b>{{ totalCritDmg }}%</b></div>
        <div v-if="totalLifesteal > 0" class="sdp-row total"><span>🧛 总吸血</span><b>{{ totalLifesteal }}%</b></div>
        <!-- 特殊被动效果 -->
        <template v-if="hasPassives">
          <div class="sdp-section">⚡ 特殊被动</div>
          <div v-if="state.passives?.heal_per_turn" class="sdp-row passive-row"><span>💚 回春</span><b>+{{ state.passives.heal_per_turn }}/回合</b><span class="sdp-desc">每回合攻击后自动恢复HP</span></div>
          <div v-if="state.passives?.reflect_pct" class="sdp-row passive-row"><span>🌵 反弹</span><b>{{ state.passives.reflect_pct }}%</b><span class="sdp-desc">受到伤害时反弹给怪物</span></div>
          <div v-if="state.passives?.first_hit_shield" class="sdp-row passive-row"><span>⚡ 首击护盾</span><b>-{{ state.passives.first_hit_shield }}</b><span class="sdp-desc">每场战斗首次被击减免固定伤害</span></div>
          <div v-if="state.passives?.dodge_pct" class="sdp-row passive-row"><span>🍀 闪避</span><b>{{ state.passives.dodge_pct }}%</b><span class="sdp-desc">受攻击时有概率完全闪避</span></div>
          <div v-if="state.passives?.bonus_exp_pct" class="sdp-row passive-row"><span>📖 经验加成</span><b>+{{ state.passives.bonus_exp_pct }}%</b><span class="sdp-desc">击杀怪物时额外获得经验</span></div>
          <div v-if="state.passives?.multi_strike" class="sdp-row passive-row"><span>⚡ 连击</span><b>{{ state.passives.multi_strike }}%</b><span class="sdp-desc">每次攻击有概率发动70%伤害的额外一击</span></div>
          <div v-if="state.passives?.execute_pct" class="sdp-row passive-row"><span>💀 斩杀</span><b>&lt;{{ state.passives.execute_pct }}%</b><span class="sdp-desc">怪物HP低于此比例时直接斩杀</span></div>
          <div v-if="state.passives?.battle_heal" class="sdp-row passive-row"><span>🏥 战后恢复</span><b>{{ state.passives.battle_heal }}%</b><span class="sdp-desc">每次战斗胜利后恢复最大HP的比例</span></div>
          <div v-if="state.passives?.block_chance" class="sdp-row passive-row"><span>🛡️ 格挡</span><b>{{ state.passives.block_chance }}%</b><span class="sdp-desc">受到攻击时有概率完美格挡免伤</span></div>
          <div v-if="state.passives?.revive" class="sdp-row passive-row"><span>🔥 凤凰重生</span><b>×{{ state.passives.revive }}</b><span class="sdp-desc">致命伤害时自动复活（恢复30%HP）</span></div>
          <div v-if="state.passives?.random_buff" class="sdp-row passive-row"><span>🎲 随机增益</span><b>激活</b><span class="sdp-desc">每回合战斗获得随机临时增益</span></div>
          <div v-if="state.passives?.crit_heal" class="sdp-row passive-row"><span>💜 暴击回血</span><b>{{ state.passives.crit_heal }}%</b><span class="sdp-desc">暴击时回复暴击伤害百分比的HP</span></div>
          <div v-if="state.passives?.overkill_heal" class="sdp-row passive-row"><span>🩸 溢出回血</span><b>{{ state.passives.overkill_heal }}%</b><span class="sdp-desc">击杀怪物时溢出伤害转化为HP</span></div>
        </template>
        <!-- 已获得的祝福列表 -->
        <template v-if="state.blessings?.length">
          <div class="sdp-section">✨ 已获得祝福</div>
          <div class="sdp-blessings">
            <span v-for="(b, i) in state.blessings" :key="i" class="sdp-bless" :class="'buff-' + (b.rarity || 'common')">{{ b.name }}<span v-if="b.count > 1">×{{ b.count }}</span></span>
          </div>
        </template>
      </div>
      <!-- 临时buff/debuff状态栏 -->
      <div v-if="state.timed_buffs?.length" class="buffs-bar">
        <span v-for="tb in state.timed_buffs" :key="tb.id"
              class="tb-tag" :class="'tb-' + tb.type"
              @click.stop="showTip(tb.name + ': ' + tb.desc + ' (来源: ' + tb.source + ')')">
          {{ tb.name }}<span class="tb-turns">{{ tb.turns_left }}{{ tb.scope === 'combat' ? '回合' : '层' }}</span>
        </span>
      </div>
    </div>

    <!-- 日志 (紧凑) -->
    <div class="log-area" ref="logRef">
      <div v-for="(msg, i) in state.log" :key="i" class="log-line">{{ msg }}</div>
    </div>

    <!-- 楼层诅咒 -->
    <div v-if="state.floor_curse && !state.game_over" class="curse-banner">
      {{ state.floor_curse.name }} — {{ state.floor_curse.desc }}
    </div>

    <!-- 遇遮信息行 -->
    <div v-if="state.encounter && !state.game_over" class="enc-row"
         :class="{ 'enc-clickable': enc.type === 'monster' || enc.type === 'boss' }"
         @click.stop="(enc.type === 'monster' || enc.type === 'boss') && (showMonsterDetail = !showMonsterDetail)">
      <template v-if="enc.type === 'monster' || enc.type === 'boss'">
        <span class="enc-icon">{{ enc.type === 'boss' ? '🐉' : (enc.elite ? '⭐' : '👾') }}</span>
        <span class="enc-name">{{ enc.name }}</span>
        <span v-if="enc.elite && enc.ability" class="elite-tag" @click.stop="showTip(enc.ability.name + ': ' + enc.ability.desc)">{{ enc.ability.name }}</span>
        <span class="enc-stat atk">⚔️{{ enc.monster_attack }}</span>
        <span v-if="enc.monster_defense > 0" class="enc-stat def">🛡️{{ enc.monster_defense }}</span>
        <div class="monster-hp">
          <div class="monster-hp-fill" :style="{ width: monsterHpPct + '%' }"></div>
          <span>{{ enc.monster_hp }}/{{ enc.monster_max_hp }}</span>
        </div>
      </template>
      <template v-else-if="enc.type === 'chest'"><span class="enc-icon">🎁</span><span class="enc-name">发现宝箱！</span></template>
      <template v-else-if="enc.type === 'trap'"><span class="enc-icon">⚠️</span><span class="enc-name">发现陷阱！</span></template>
      <template v-else-if="enc.type === 'shop'">
        <span class="enc-icon">🏪</span><span class="enc-name">{{ enc.name || '商店' }}</span>
        <span class="shop-wallet">💰{{ state.exp_earned }}</span>
      </template>
      <template v-else-if="enc.type === 'blessing'"><span class="enc-icon">✨</span><span class="enc-name">{{ enc.name }}</span></template>
    </div>
    <!-- 怪物详情面板 -->
    <div v-if="showMonsterDetail && (enc.type === 'monster' || enc.type === 'boss') && !state.game_over"
         class="monster-detail-panel" @click.stop>
      <div class="sdp-title">
        {{ enc.type === 'boss' ? '🐉' : (enc.elite ? '⭐' : '👾') }} {{ enc.name }}
        <span class="sdp-close" @click="showMonsterDetail = false">✕</span>
      </div>
      <div class="sdp-section">📊 怪物属性</div>
      <div class="sdp-row"><span>❤️ 生命</span><b>{{ enc.monster_hp }} / {{ enc.monster_max_hp }}</b></div>
      <div class="sdp-row"><span>⚔️ 攻击</span><b>{{ enc.monster_attack }}</b><span class="sdp-desc">每回合对你造成的伤害（减去你的防御）</span></div>
      <div class="sdp-row"><span>🛡️ 防御</span><b>{{ enc.monster_defense || 0 }}</b><span class="sdp-desc">减少你的攻击伤害</span></div>
      <template v-if="enc.elite && enc.ability">
        <div class="sdp-section">⭐ 精英能力</div>
        <div class="sdp-row"><span>{{ enc.ability.name }}</span><b class="ability-desc">{{ enc.ability.desc }}</b></div>
      </template>
      <template v-if="enc.type === 'boss'">
        <div class="sdp-section">🐉 Boss</div>
        <div class="sdp-row"><span class="sdp-desc">Boss战无法逃跑，击败后获得大量经验</span></div>
      </template>
    </div>

    <!-- 🎒 背包 (紧跟遭遇信息) -->
    <div v-if="state.backpack && !state.game_over" class="bp-section" @click.stop>
      <div class="bp-header">
        <div class="bp-title-row">
          <span class="bp-title">🎒 {{ state.backpack.rows }}×{{ state.backpack.cols }}</span>
          <button v-if="state.backpack.expand_cost != null" class="bp-expand-btn"
                  :disabled="state.exp_earned < state.backpack.expand_cost"
                  @click.stop="expandBackpack">
            📐 扩容({{ state.backpack.expand_cost }}E)
          </button>
        </div>
        <div v-if="bpStats" class="bp-stat-tags">
          <span v-if="bpStats.atk">⚔️+{{ bpStats.atk }}</span>
          <span v-if="bpStats.def">🛡️+{{ bpStats.def }}</span>
          <span v-if="bpStats.crit">🎯+{{ bpStats.crit }}%</span>
          <span v-if="bpStats.crit_damage">💥+{{ bpStats.crit_damage }}%</span>
          <span v-if="bpStats.lifesteal">🧛+{{ bpStats.lifesteal }}%</span>
          <span v-if="bpStats.max_hp">❤️+{{ bpStats.max_hp }}</span>
          <span v-if="bpStats.exp_bonus">📖+{{ bpStats.exp_bonus }}%</span>
        </div>
      </div>
      <!-- 套装 / 连锁 / 被动 提示栏 -->
      <div v-if="state.backpack.active_sets?.length || state.backpack.chain_bonus || state.backpack.passives" class="bp-bonus-bar">
        <span v-for="s in (state.backpack.active_sets || [])" :key="s.id" class="bp-bonus-tag set" @click.stop="showTip(s.name + ' ' + s.desc)">{{ s.name }}({{ s.pieces }}/{{ s.total }})</span>
        <span v-if="state.backpack.chain_bonus" class="bp-bonus-tag chain" @click.stop="showTip('🔗 连锁加成: 同一行或列放置3个以上同类型物品可获得额外属性加成')">🔗 连锁加成</span>
        <span v-if="state.backpack.passives?.heal_per_turn" class="bp-bonus-tag passive" @click.stop="showTip('💚 回春: 每回合攻击后自动恢复' + state.backpack.passives.heal_per_turn + 'HP')">💚 回春+{{ state.backpack.passives.heal_per_turn }}/回合</span>
        <span v-if="state.backpack.passives?.reflect_pct" class="bp-bonus-tag passive" @click.stop="showTip('🌵 反弹: 受到伤害时自动反弹' + state.backpack.passives.reflect_pct + '%给怪物')">🌵 反弹{{ state.backpack.passives.reflect_pct }}%</span>
        <span v-if="state.backpack.passives?.first_hit_shield" class="bp-bonus-tag passive" @click.stop="showTip('⚡ 首击护盾: 每场战斗首次被攻击时减免' + state.backpack.passives.first_hit_shield + '伤害')">⚡ 首击减{{ state.backpack.passives.first_hit_shield }}</span>
        <span v-if="state.backpack.passives?.dodge_pct" class="bp-bonus-tag passive" @click.stop="showTip('🍀 闪避: 每次受攻击时有' + state.backpack.passives.dodge_pct + '%概率完全闪避')">🍀 闪避{{ state.backpack.passives.dodge_pct }}%</span>
        <span v-if="state.backpack.passives?.bonus_exp_pct" class="bp-bonus-tag passive" @click.stop="showTip('📖 经验加成: 击杀怪物时额外获得' + state.backpack.passives.bonus_exp_pct + '%经验')">📖 击杀EXP+{{ state.backpack.passives.bonus_exp_pct }}%</span>
        <span v-if="state.backpack.passives?.multi_strike" class="bp-bonus-tag passive legendary" @click.stop="showTip('⚡ 连击: 每次攻击有' + state.backpack.passives.multi_strike + '%概率发动70%伤害的额外一击')">⚡ 连击{{ state.backpack.passives.multi_strike }}%</span>
        <span v-if="state.backpack.passives?.execute_pct" class="bp-bonus-tag passive legendary" @click.stop="showTip('💀 斩杀: 怪物HP低于' + state.backpack.passives.execute_pct + '%时直接斩杀')">💀 斩杀{{ state.backpack.passives.execute_pct }}%</span>
        <span v-if="state.backpack.passives?.battle_heal" class="bp-bonus-tag passive legendary" @click.stop="showTip('🏥 战后恢复: 每次战斗胜利后恢复' + state.backpack.passives.battle_heal + '%最大HP')">🏥 战后恢复{{ state.backpack.passives.battle_heal }}%</span>
        <span v-if="state.backpack.passives?.block_chance" class="bp-bonus-tag passive legendary" @click.stop="showTip('🛡️ 格挡: 受到攻击时有' + state.backpack.passives.block_chance + '%概率完美格挡，完全免伤')">🛡️ 格挡{{ state.backpack.passives.block_chance }}%</span>
        <span v-if="state.backpack.passives?.revive" class="bp-bonus-tag passive legendary" @click.stop="showTip('🔥 凤凰重生: 致命伤害时自动复活，恢复30%HP（剩余' + state.backpack.passives.revive + '次）')">🔥 凤凰重生×{{ state.backpack.passives.revive }}</span>
        <span v-if="state.backpack.passives?.random_buff" class="bp-bonus-tag passive legendary" @click.stop="showTip('🎲 随机增益: 每回合战斗获得随机临时增益（攻击/防御/暴伤/回血）')">🎲 随机增益</span>
        <span v-if="state.backpack.passives?.crit_heal" class="bp-bonus-tag passive legendary" @click.stop="showTip('💜 暴击回血: 暴击时回复暴击伤害' + state.backpack.passives.crit_heal + '%的HP')">💜 暴击回血{{ state.backpack.passives.crit_heal }}%</span>
        <span v-if="state.backpack.passives?.overkill_heal" class="bp-bonus-tag passive legendary" @click.stop="showTip('🩸 溢出回血: 击杀怪物时溢出伤害的' + state.backpack.passives.overkill_heal + '%转化为HP')">🩸 溢出回血{{ state.backpack.passives.overkill_heal }}%</span>
      </div>
      <div class="bp-grid-wrap" ref="gridRef" :style="gridWrapStyle">
        <!-- 底格 -->
        <div v-for="r in state.backpack.rows" :key="'r' + r" class="bp-row">
          <div v-for="c in state.backpack.cols" :key="'c' + c" class="bp-cell"
               :class="{ 'bp-cell-occ': isCellOcc(r-1, c-1), 'bp-cell-target': (moveMode && canMoveTo(r-1, c-1)) || isDragTarget(r-1, c-1), 'bp-cell-bonus': isBonusCell(r-1, c-1) }"
               @click.stop="isBonusCell(r-1, c-1) && !moveMode ? showTip('★ 特殊区域: 物品放在此处基础属性+50%') : onCellClick(r-1, c-1)">
            <span v-if="moveMode && canMoveTo(r-1, c-1)" class="cell-hint">✦</span>
            <span v-else-if="isBonusCell(r-1, c-1) && !isCellOcc(r-1, c-1)" class="cell-hint bonus-star">★</span>
          </div>
        </div>
        <!-- 物品 -->
        <div v-for="item in state.backpack.items" :key="item.uid" class="bp-item"
             :class="['rarity-' + item.rarity, { 'bp-sel': selectedUid === item.uid, 'bp-cons': item.consumable, 'bp-linked': adjacentUids.has(item.uid), 'bp-cursed': item.cursed, 'bp-enchanted': item.enchants?.length > 0, 'bp-merge-target': (mergeMode && item.uid !== selectedUid && item.id === selItem?.id && item.can_merge) || (dragMergeTarget?.uid === item.uid) }]"
             :style="bpItemStyle(item)" @click.stop="onItemClick(item)"
             @touchstart.prevent="onDragStart(item, $event)"
             @mousedown.prevent="onDragStart(item, $event)">
          <span class="bp-item-icon">{{ item.icon }}</span>
          <span v-if="item.enchants?.length" class="bp-ench-dot">{{ item.enchants.length }}</span>
        </div>
        <!-- 拖拽幽灵 -->
        <div v-if="isDragging && dragItem" class="bp-drag-ghost"
             :class="['rarity-' + dragItem.rarity, { 'drag-merge': !!dragMergeTarget }]"
             :style="dragGhostStyle">
          <span class="bp-item-icon">{{ dragItem.icon }}</span>
          <span v-if="dragMergeTarget" class="drag-merge-icon">🔨</span>
        </div>
      </div>
      <!-- 物品操作条 (选中时出现) -->
      <div v-if="selItem && !moveMode && !mergeMode" class="bp-toolbar" @click.stop>
        <div class="bp-tb-info">
          <span class="bp-tb-name" :class="'rt-' + selItem.rarity">{{ selItem.icon }} {{ selItem.name }}</span>
          <span class="bp-tb-desc">{{ selItem.desc }}</span>
          <span v-if="selItem.cursed" class="bp-tb-curse" @click.stop="showTip('💀 诅咒: 此物品有负面效果，将净化石放在旁边可抵消')">💀诅咒</span>
          <span v-if="selItem.purified" class="bp-tb-purified" @click.stop="showTip('🔮 净化: 净化石已抵消此物品的诅咒负面效果')">🔮净化</span>
          <span v-if="selItem.adj_desc" class="bp-tb-adj">🔗{{ selItem.adj_desc }}</span>
          <span v-if="selItem.passive" class="bp-tb-passive">⚡{{ passiveDesc(selItem.passive) }}</span>
          <template v-if="selItem.enchants?.length">
            <span v-for="(e, i) in selItem.enchants" :key="i" class="ench-tag">{{ e.icon }}{{ e.name }}+{{ e.value }}</span>
          </template>
        </div>
        <div class="bp-tb-btns">
          <button v-if="selItem.consumable" class="tb-btn use" @click="useItem(selItem.uid)">💊用</button>
          <button class="tb-btn move" @click="enterMoveMode">📦移</button>
          <button v-if="!selItem.consumable && selItem.w !== selItem.h" class="tb-btn rotate" @click="rotateItem(selItem.uid)">🔄转</button>
          <button v-if="!selItem.consumable" class="tb-btn enchant" :disabled="state.exp_earned < (state.backpack?.enchant_cost || 99)"
                  @click="enchantItem(selItem.uid)">💎{{ state.backpack?.enchant_cost || 15 }}E</button>
          <button v-if="selItem.can_merge" class="tb-btn merge" @click="enterMergeMode">🔨合</button>
          <button class="tb-btn sell" @click="sellItem(selItem.uid)">💰{{ selItem.sell_price }}E</button>
          <button class="tb-btn discard" @click="discardItem(selItem.uid)">🗑️</button>
        </div>
      </div>
      <!-- 合成模式提示 -->
      <div v-if="mergeMode" class="bp-move-hint" @click.stop>
        🔨 点击另一个 <b>{{ selItem?.name }}</b> 进行合成 → {{ mergeTargetName }}
        <button class="tb-btn cancel" @click="exitMergeMode">✕取消</button>
      </div>
      <!-- 移动模式提示 -->
      <div v-if="moveMode" class="bp-move-hint" @click.stop>
        📦 点击网格放置 <b>{{ selItem?.name }}</b>
        <button class="tb-btn cancel" @click="exitMoveMode">✕取消</button>
      </div>
    </div>

    <!-- 操作区 (在背包下面，紧凑排布) -->
    <div v-if="state.encounter && !state.game_over && !state.encounter_resolved" class="action-zone">
      <!-- 怪物/Boss 动作 -->
      <template v-if="enc.type === 'monster' || enc.type === 'boss'">
        <button class="act-btn fight" @click="doAction('fight')">⚔️战斗</button>
        <button class="act-btn flee" @click="doAction('flee')">🏃逃跑</button>
      </template>
      <!-- 宝箱 -->
      <template v-else-if="enc.type === 'chest'">
        <button class="act-btn chest" @click="doAction('open')">🎁打开</button>
      </template>
      <!-- 陷阱 -->
      <template v-else-if="enc.type === 'trap'">
        <button class="act-btn disarm" @click="doAction('disarm')">🔧拆除(60%)</button>
        <button class="act-btn bypass" @click="doAction('bypass')">🚶绕过</button>
      </template>
      <!-- 商店 -->
      <template v-else-if="enc.type === 'shop'">
        <div class="shop-items">
          <div v-for="(si, idx) in shopItems" :key="idx" class="shop-card"
               :class="['rarity-' + si.rarity, { 'shop-disabled': state.exp_earned < si.price }]"
               @click.stop="buyItem(Number(idx))">
            <span class="si-icon">{{ si.icon }}</span>
            <span class="si-name">{{ si.name }}</span>
            <span v-if="si.cursed" class="si-tag cursed">💀诅咒</span>
            <span v-if="si.passive" class="si-tag passive">⚡被动</span>
            <span class="si-info">{{ si.w }}×{{ si.h }} {{ si.desc }}</span>
            <span class="si-price" :class="{ disabled: state.exp_earned < si.price }">{{ si.price }}E</span>
          </div>
        </div>
        <button class="act-btn skip" @click="doAction('skip')">🚶离开</button>
      </template>
      <!-- 祝福 -->
      <template v-else-if="enc.type === 'blessing'">
        <div class="blessing-list">
          <button v-for="ch in (enc.choices || [])" :key="ch.id" class="bless-btn" :class="'bless-' + (ch.rarity || 'common')" @click="chooseBlessing(ch.id)">
            <b>{{ ch.name }}</b><span>{{ ch.desc }}</span>
          </button>
        </div>
        <button class="act-btn reroll"
                :disabled="state.exp_earned < rerollCost"
                @click="rerollBlessing">
          🎲 换一批({{ rerollCost }}E)
        </button>
      </template>
    </div>

    <!-- 遭遇已解决 → 下一层 / 撤退 -->
    <div v-if="state.encounter_resolved && !state.game_over" class="action-zone next-zone">
      <div v-if="state.next_floor_preview" class="next-floor-hint">
        <span class="nfh-icon">{{ state.next_floor_preview.icon }}</span>
        <span class="nfh-text">
          下一层({{ state.next_floor_preview.floor }}F):
          <b :class="'nfh-type-' + state.next_floor_preview.type">{{ state.next_floor_preview.name }}</b>
          <span v-if="state.next_floor_preview.is_final" class="nfh-final">🏆 最终Boss</span>
          <span v-if="state.next_floor_preview.hint" class="nfh-sub">{{ state.next_floor_preview.hint }}</span>
        </span>
      </div>
      <button class="act-btn next" @click="doAction('next_floor')">
        {{ !state.endless && state.floor >= state.max_floor ? '🏆完成探险' : '📍下一层' }}
      </button>
    </div>

    <!-- 结果 -->
    <div v-if="state.game_over" class="game-result" :class="resultClass">
      <div class="result-title">{{ resultTitle }}</div>
      <div class="result-detail">{{ state.endless ? `到达第 ${state.floor} 层` : `通过 ${state.floors_cleared}/${state.max_floor} 层` }}</div>
      <div class="result-exp" :class="{ lost: !state.exp_earned || state.abandoned }">
        {{ state.exp_earned > 0 && !state.abandoned ? `获得 ${state.exp_earned} EXP` : '未获得经验' }}
      </div>
    </div>

    <!-- 撤退 (无尽，永远最底部) -->
    <button v-if="state.endless && !state.game_over" class="retreat-btn" :class="{ confirming: retreatConfirm }"
            @click="retreatConfirm ? doAction('retreat') : (retreatConfirm = true)">
      {{ retreatConfirm ? '⚠️ 确认撤退？点击确认' : `🚪 撤退(保留${state.exp_earned}EXP)` }}
    </button>
    <!-- 移动端点击提示气泡 -->
    <Transition name="tip-fade">
      <div v-if="tipText" class="tap-tip" @click.stop="tipText = ''">
        {{ tipText }}
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { adventureSound, adventureBGM, warmUp } from '../../utils/gameSound'

const props = defineProps<{ state: any }>()
const emit = defineEmits<{ (e: 'action', action: any): void }>()
const logRef = ref<HTMLDivElement>()
const selectedUid = ref<number | null>(null)
const moveMode = ref(false)
const mergeMode = ref(false)
const showStatDetail = ref(false)
const showMonsterDetail = ref(false)
const retreatConfirm = ref(false)
const tipText = ref('')
const cellSize = 36

// 长按拖拽
const dragItem = ref<any>(null)
const dragOffset = ref({ x: 0, y: 0 })
const dragPos = ref({ x: 0, y: 0 })
const longPressTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const isDragging = ref(false)
const justDragged = ref(false)
const gridRef = ref<HTMLDivElement>()

const enc = computed(() => props.state.encounter || {})
const bpStats = computed(() => props.state.bp_stats || null)
const hpPct = computed(() => (props.state.hp / props.state.max_hp) * 100)
const hpColor = computed(() => hpPct.value > 60 ? '#4caf50' : hpPct.value > 30 ? '#ff9800' : '#f44336')
const monsterHpPct = computed(() => {
  const e = enc.value
  return e.monster_max_hp ? (e.monster_hp / e.monster_max_hp) * 100 : 0
})
const totalAtk = computed(() => (props.state.attack || 0) + (bpStats.value?.atk || 0))
const totalDef = computed(() => (props.state.defense || 0) + (bpStats.value?.def || 0))
const totalCrit = computed(() => Math.min((props.state.crit_chance || 0) + (bpStats.value?.crit || 0), 100))
const totalCritDmg = computed(() => (props.state.crit_damage || 180) + (bpStats.value?.crit_damage || 0))
const totalLifesteal = computed(() => (props.state.lifesteal || 0) + (bpStats.value?.lifesteal || 0))
const hasPassives = computed(() => {
  const p = props.state.passives
  return p && Object.values(p).some((v: any) => v)
})
const shopItems = computed(() => enc.value?.shop_items || [])

const selItem = computed(() => {
  if (!selectedUid.value || !props.state.backpack) return null
  return props.state.backpack.items?.find((i: any) => i.uid === selectedUid.value) || null
})

const gridWrapStyle = computed(() => {
  const bp = props.state.backpack
  if (!bp) return {}
  return { width: bp.cols * cellSize + 'px', height: bp.rows * cellSize + 'px' }
})

const resultClass = computed(() => {
  if (props.state?.abandoned) return 'lose'
  if (props.state?.retreated) return 'win'
  return props.state?.floors_cleared >= props.state?.max_floor ? 'win' : 'lose'
})
const resultTitle = computed(() => {
  if (props.state?.abandoned) return '🏳️ 已放弃'
  if (props.state?.retreated) return '🚪 安全撤退！'
  if (!props.state?.endless && props.state?.floors_cleared >= props.state?.max_floor) return '🏆 全部通关！'
  if (props.state?.hp <= 0) return '💀 探险失败'
  return '探险结束'
})

watch(() => props.state.log?.length, () => {
  nextTick(() => { if (logRef.value) logRef.value.scrollTop = logRef.value.scrollHeight })
})
watch(() => props.state.floor, () => { retreatConfirm.value = false; showMonsterDetail.value = false })
watch(() => props.state?.hp, (n: any, o: any) => { if (o !== undefined && n < o) adventureSound.hurt() })
watch(() => props.state?.game_over, (v) => { if (v) adventureBGM.stop() })

onMounted(() => {
  warmUp()
  // 延迟一小段让 AudioContext 完成 resume 后再开始背景音乐
  setTimeout(() => adventureBGM.start(), 300)
})
onBeforeUnmount(() => {
  adventureBGM.stop()
})
watch(() => props.state.backpack?.items?.length, () => {
  if (selectedUid.value && props.state.backpack) {
    if (!props.state.backpack.items?.find((i: any) => i.uid === selectedUid.value)) {
      selectedUid.value = null
      moveMode.value = false
      mergeMode.value = false
    }
  }
})

/* ---- 背包操作 ---- */
// 选中物品的相邻关联物品 uid 集合
const adjacentUids = computed(() => {
  const sel = selItem.value
  if (!sel || !props.state.backpack) return new Set<number>()
  const items: any[] = props.state.backpack.items || []
  // 构建占用图: (r,c) -> item
  const occ = new Map<string, any>()
  for (const it of items) {
    for (let dr = 0; dr < it.h; dr++)
      for (let dc = 0; dc < it.w; dc++)
        occ.set(`${it.row + dr},${it.col + dc}`, it)
  }
  // 找出选中物品所有格子的四方向邻居
  const linked = new Set<number>()
  for (let dr = 0; dr < sel.h; dr++) {
    for (let dc = 0; dc < sel.w; dc++) {
      const r = sel.row + dr, c = sel.col + dc
      for (const [nr, nc] of [[r-1,c],[r+1,c],[r,c-1],[r,c+1]]) {
        const nb = occ.get(`${nr},${nc}`)
        if (nb && nb.uid !== sel.uid) {
          // 类型匹配检查: sel 的 adj 规则包含 nb 的 type，或 nb 的 adj 规则包含 sel 的 type
          const selAdj = sel.adj || {}
          const nbAdj = nb.adj || {}
          if (selAdj[nb.type] || nbAdj[sel.type]) linked.add(nb.uid)
        }
      }
    }
  }
  return linked
})

function isCellOcc(r: number, c: number): boolean {
  const items = props.state.backpack?.items
  if (!items) return false
  return items.some((it: any) => r >= it.row && r < it.row + it.h && c >= it.col && c < it.col + it.w)
}

function bpItemStyle(item: any) {
  return {
    left: item.col * cellSize + 'px',
    top: item.row * cellSize + 'px',
    width: item.w * cellSize - 2 + 'px',
    height: item.h * cellSize - 2 + 'px',
  }
}

function canMoveTo(r: number, c: number): boolean {
  if (!moveMode.value || !selItem.value) return false
  const it = selItem.value
  const bp = props.state.backpack
  if (!bp) return false
  if (r + it.h > bp.rows || c + it.w > bp.cols) return false
  const items = bp.items || []
  for (let dr = 0; dr < it.h; dr++) {
    for (let dc = 0; dc < it.w; dc++) {
      const occItem = items.find((x: any) =>
        (r + dr) >= x.row && (r + dr) < x.row + x.h && (c + dc) >= x.col && (c + dc) < x.col + x.w
      )
      if (occItem && occItem.uid !== it.uid) return false
    }
  }
  return true
}

function onItemClick(item: any) {
  if (moveMode.value) return
  if (justDragged.value) { justDragged.value = false; return }
  // 合成模式: 点击同id物品 → 执行合成
  if (mergeMode.value && selItem.value && item.uid !== selItem.value.uid && item.id === selItem.value.id && item.can_merge) {
    emit('action', { action: 'merge_items', item_uid1: selItem.value.uid, item_uid2: item.uid })
    mergeMode.value = false; selectedUid.value = null
    return
  }
  mergeMode.value = false
  selectedUid.value = selectedUid.value === item.uid ? null : item.uid
  moveMode.value = false
}

function onCellClick(r: number, c: number) {
  if (moveMode.value && selItem.value && canMoveTo(r, c)) {
    emit('action', { action: 'move_item', item_uid: selItem.value.uid, row: r, col: c })
    moveMode.value = false
  }
}

function enterMoveMode() { moveMode.value = true }
function exitMoveMode() { moveMode.value = false }
function clearSelect() { if (!isDragging.value) { selectedUid.value = null; moveMode.value = false; mergeMode.value = false; showStatDetail.value = false; showMonsterDetail.value = false; tipText.value = '' } }
function showTip(text: string) { tipText.value = tipText.value === text ? '' : text }

/* ---- 新系统辅助 ---- */
function isBonusCell(r: number, c: number): boolean {
  const cells = props.state.backpack?.bonus_cells || []
  return cells.some((p: number[]) => p[0] === r && p[1] === c)
}

const mergeTargetName = computed(() => {
  if (!selItem.value?.merge_target) return ''
  const items = props.state.backpack?.items || []
  // 在商店数据中查不到名称，直接用id做简短展示
  const tid = selItem.value.merge_target
  // 先在已有物品中查（万一背包里有该物品）
  const existing = items.find((i: any) => i.id === tid)
  if (existing) return existing.icon + existing.name
  return '⬆️升级'
})

function passiveDesc(p: any): string {
  if (!p) return ''
  const parts: string[] = []
  if (p.heal_per_turn) parts.push(`每回合+${p.heal_per_turn}HP`)
  if (p.reflect_pct) parts.push(`反弹${p.reflect_pct}%伤害`)
  if (p.first_hit_shield) parts.push(`首击减${p.first_hit_shield}`)
  if (p.dodge_pct) parts.push(`${p.dodge_pct}%闪避`)
  if (p.bonus_exp_pct) parts.push(`击杀EXP+${p.bonus_exp_pct}%`)
  return parts.join(' ')
}

function sellItem(uid: number) {
  emit('action', { action: 'sell_item', item_uid: uid })
  selectedUid.value = null; moveMode.value = false; mergeMode.value = false
}

function enchantItem(uid: number) {
  emit('action', { action: 'enchant_item', item_uid: uid })
}

function enterMergeMode() { mergeMode.value = true }
function exitMergeMode() { mergeMode.value = false }

/* ---- 长按拖拽 ---- */
const LONG_PRESS_MS = 300
const dragTargetCell = ref<{ r: number; c: number } | null>(null)
const dragMergeTarget = ref<any>(null)

const dragGhostStyle = computed(() => {
  if (!dragItem.value) return {}
  return {
    left: dragPos.value.x - dragOffset.value.x + 'px',
    top: dragPos.value.y - dragOffset.value.y + 'px',
    width: dragItem.value.w * cellSize - 2 + 'px',
    height: dragItem.value.h * cellSize - 2 + 'px',
  }
})

function isDragTarget(r: number, c: number): boolean {
  if (!isDragging.value || !dragItem.value || !dragTargetCell.value) return false
  if (dragMergeTarget.value) return false  // merge时由物品高亮代替格子高亮
  const tr = dragTargetCell.value.r, tc = dragTargetCell.value.c
  return r >= tr && r < tr + dragItem.value.h && c >= tc && c < tc + dragItem.value.w
}

function onDragStart(item: any, e: TouchEvent | MouseEvent) {
  if (moveMode.value) return
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  const startItem = item
  // Shared cleanup for pre-drag listeners
  let preDragCleaned = false
  const cleanupPreDrag = () => {
    if (preDragCleaned) return
    preDragCleaned = true
    document.removeEventListener('touchend', quickTap)
    document.removeEventListener('mouseup', quickTap)
    document.removeEventListener('touchmove', cancelDrag)
    document.removeEventListener('mousemove', cancelDrag)
  }
  const quickTap = () => {
    if (preDragCleaned) return  // long-press already took over
    if (longPressTimer.value) { clearTimeout(longPressTimer.value); longPressTimer.value = null }
    cleanupPreDrag()
    onItemClick(startItem)
  }
  const cancelDrag = () => {
    if (longPressTimer.value) { clearTimeout(longPressTimer.value); longPressTimer.value = null }
    cleanupPreDrag()
  }
  longPressTimer.value = setTimeout(() => {
    cleanupPreDrag()  // remove quickTap/cancel before entering drag
    isDragging.value = true
    dragItem.value = startItem
    selectedUid.value = startItem.uid
    moveMode.value = false
    mergeMode.value = false
    const rect = gridRef.value?.getBoundingClientRect()
    if (rect) {
      dragOffset.value = { x: cellSize * startItem.w / 2, y: cellSize * startItem.h / 2 }
      dragPos.value = { x: clientX - rect.left, y: clientY - rect.top }
    }
    updateDragTarget()
    document.addEventListener('touchmove', onDragMove, { passive: false })
    document.addEventListener('mousemove', onDragMove)
    document.addEventListener('touchend', onDragEnd)
    document.addEventListener('mouseup', onDragEnd)
  }, LONG_PRESS_MS)
  document.addEventListener('touchend', quickTap, { once: true })
  document.addEventListener('mouseup', quickTap, { once: true })
  document.addEventListener('touchmove', cancelDrag, { once: true })
  document.addEventListener('mousemove', cancelDrag, { once: true })
}

function onDragMove(e: TouchEvent | MouseEvent) {
  e.preventDefault()
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  const rect = gridRef.value?.getBoundingClientRect()
  if (rect) {
    dragPos.value = { x: clientX - rect.left, y: clientY - rect.top }
  }
  updateDragTarget()
}

function updateDragTarget() {
  dragMergeTarget.value = null
  if (!dragItem.value || !gridRef.value) { dragTargetCell.value = null; return }
  const cx = dragPos.value.x - dragOffset.value.x + cellSize * dragItem.value.w / 2
  const cy = dragPos.value.y - dragOffset.value.y + cellSize * dragItem.value.h / 2
  const c = Math.floor(cx / cellSize)
  const r = Math.floor(cy / cellSize)
  const bp = props.state.backpack
  if (!bp || r < 0 || c < 0 || r + dragItem.value.h > bp.rows || c + dragItem.value.w > bp.cols) {
    dragTargetCell.value = null; return
  }
  // Check collision excluding self; detect merge-candidate
  const items = bp.items || []
  const colliders = new Set<number>()
  for (let dr = 0; dr < dragItem.value.h; dr++) {
    for (let dc = 0; dc < dragItem.value.w; dc++) {
      const occ = items.find((x: any) => (r+dr) >= x.row && (r+dr) < x.row + x.h && (c+dc) >= x.col && (c+dc) < x.col + x.w)
      if (occ && occ.uid !== dragItem.value.uid) colliders.add(occ.uid)
    }
  }
  if (colliders.size === 0) {
    // Empty target → normal move
    dragTargetCell.value = { r, c }
  } else if (colliders.size === 1) {
    // Single collider → check if mergeable
    const targetUid = [...colliders][0]
    const target = items.find((x: any) => x.uid === targetUid)
    if (target && target.id === dragItem.value.id && dragItem.value.can_merge && target.can_merge) {
      dragMergeTarget.value = target
      dragTargetCell.value = { r: target.row, c: target.col }
    } else {
      dragTargetCell.value = null
    }
  } else {
    dragTargetCell.value = null
  }
}

function onDragEnd() {
  document.removeEventListener('touchmove', onDragMove)
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('touchend', onDragEnd)
  document.removeEventListener('mouseup', onDragEnd)
  if (isDragging.value && dragItem.value) {
    if (dragMergeTarget.value) {
      // 拖拽合并
      emit('action', { action: 'merge_items', item_uid1: dragItem.value.uid, item_uid2: dragMergeTarget.value.uid })
      selectedUid.value = null
    } else if (dragTargetCell.value) {
      const { r, c } = dragTargetCell.value
      if (r !== dragItem.value.row || c !== dragItem.value.col) {
        emit('action', { action: 'move_item', item_uid: dragItem.value.uid, row: r, col: c })
      }
    }
  }
  if (isDragging.value) justDragged.value = true
  isDragging.value = false
  dragItem.value = null
  dragTargetCell.value = null
  dragMergeTarget.value = null
  if (longPressTimer.value) { clearTimeout(longPressTimer.value); longPressTimer.value = null }
}

function rotateItem(uid: number) {
  emit('action', { action: 'rotate_item', item_uid: uid })
}

function expandBackpack() {
  emit('action', { action: 'expand_backpack' })
}

function useItem(uid: number) {
  emit('action', { action: 'use_item', item_uid: uid })
  selectedUid.value = null; moveMode.value = false
}

function discardItem(uid: number) {
  emit('action', { action: 'discard_item', item_uid: uid })
  selectedUid.value = null; moveMode.value = false
}

function doAction(act: string) {
  warmUp()
  if (act === 'fight') adventureSound.attack()
  else if (act === 'next_floor') adventureSound.nextFloor()
  else if (act === 'open') adventureSound.chest()
  emit('action', { action: act })
}

function buyItem(idx: number) {
  const si = shopItems.value[idx]
  if (!si) return
  warmUp()
  adventureSound.shop()
  emit('action', { action: 'buy_item', shop_index: idx })
}

function chooseBlessing(id: string) {
  warmUp()
  adventureSound.buff()
  emit('action', { action: 'choose_blessing', blessing_id: id })
}

const rerollCost = computed(() => {
  const cnt = enc.value?.reroll_count || 0
  return 8 + cnt * 8
})

function rerollBlessing() {
  emit('action', { action: 'reroll_blessing' })
}
</script>

<style scoped>
.adventure-game { padding: 6px; font-size: 13px; }

/* ---- 状态栏 ---- */
.status-bar { margin-bottom: 4px; }
.hp-bar {
  position: relative; height: 20px;
  background: var(--theme-bg-secondary, #eee);
  border-radius: 10px; overflow: hidden; margin-bottom: 4px;
}
.hp-fill { height: 100%; border-radius: 10px; transition: width .3s, background .3s; }
.hp-text {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: bold; color: var(--theme-text-primary, #333);
  text-shadow: 0 0 3px var(--theme-bg-card, #fff);
}
.stats-row { display: flex; justify-content: center; gap: 8px; font-size: 12px; flex-wrap: wrap; cursor: pointer; }
/* 属性详情面板 */
.stat-detail-panel {
  margin-top: 4px; padding: 8px 10px; border-radius: 8px;
  background: var(--theme-bg-card, #fff); border: 1px solid var(--theme-border, #ddd);
  box-shadow: 0 2px 12px rgba(0,0,0,.1); font-size: 12px; position: relative; z-index: 20;
}
.sdp-title { font-size: 13px; font-weight: 700; margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between; }
.sdp-close { cursor: pointer; font-size: 14px; color: var(--theme-text-tertiary, #aaa); padding: 0 4px; }
.sdp-close:hover { color: var(--theme-text-primary, #333); }
.sdp-section { font-size: 11px; font-weight: 700; color: var(--theme-primary, #ff9800); margin: 5px 0 2px; border-top: 1px solid var(--theme-border-light, #eee); padding-top: 4px; }
.sdp-row { display: flex; align-items: center; gap: 6px; padding: 1px 0; color: var(--theme-text-secondary, #555); }
.sdp-row b { color: var(--theme-text-primary, #333); min-width: 40px; }
.sdp-row .sdp-desc { font-size: 10px; color: var(--theme-text-tertiary, #999); }
.sdp-row.total { font-weight: 600; color: var(--theme-text-primary, #333); }
.sdp-row.total b { color: var(--theme-primary, #ff9800); }
@keyframes pulse { from { opacity: .7 } to { opacity: 1 } }
.buffs-bar { display: flex; flex-wrap: wrap; gap: 3px; justify-content: center; margin-top: 3px; }
/* 临时buff/debuff标签 */
.tb-tag {
  font-size: 10px; padding: 1px 6px; border-radius: 8px; white-space: nowrap;
  display: inline-flex; align-items: center; gap: 2px;
}
.tb-buff {
  background: rgba(76,175,80,.12); border: 1px solid rgba(76,175,80,.35); color: #2e7d32;
}
.tb-debuff {
  background: rgba(229,57,53,.1); border: 1px solid rgba(229,57,53,.3); color: #c62828;
  animation: debuff-pulse 1.5s ease-in-out infinite alternate;
}
@keyframes debuff-pulse { from { opacity: .85 } to { opacity: 1 } }
.tb-turns { font-size: 9px; font-weight: 700; margin-left: 2px; opacity: .75; }
/* 已获得祝福（仅在属性面板内显示） */
.sdp-blessings { display: flex; flex-wrap: wrap; gap: 3px; padding: 2px 0; }
.sdp-bless {
  font-size: 10px; padding: 1px 5px; border-radius: 8px; white-space: nowrap;
}
.buff-common { background: rgba(158,158,158,.1); border: 1px solid rgba(158,158,158,.3); color: #757575; }
.buff-rare { background: rgba(33,150,243,.1); border: 1px solid rgba(33,150,243,.3); color: #1976d2; }
.buff-epic { background: rgba(156,39,176,.1); border: 1px solid rgba(156,39,176,.3); color: #8e24aa; }
.buff-legendary { background: rgba(255,152,0,.12); border: 1px solid rgba(255,152,0,.4); color: #e65100; font-weight: 600; }

/* ---- 日志 ---- */
.log-area {
  height: 72px; overflow-y: auto;
  background: var(--theme-bg-secondary, #f9f9f9);
  border-radius: 6px; padding: 4px 6px; margin-bottom: 4px;
  font-size: 12px; line-height: 1.5;
}
.log-line { color: var(--theme-text-secondary, #555); }

/* ---- 遭遇信息行 ---- */
.enc-row {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  padding: 6px 8px; margin-bottom: 4px;
  background: var(--theme-bg-card, #fff); border-radius: 8px;
  border: 1px solid var(--theme-border-light, #eee);
}
.enc-clickable { cursor: pointer; }
.enc-clickable:hover { border-color: var(--theme-primary, #ff9800); box-shadow: 0 1px 6px rgba(255,152,0,.12); }
.enc-icon { font-size: 22px; }
.enc-name { font-size: 14px; font-weight: bold; }
.enc-stat { font-size: 11px; font-weight: 600; }
.enc-stat.atk { color: #e53935; }
.enc-stat.def { color: #757575; }
.elite-tag {
  font-size: 9px; padding: 1px 6px; border-radius: 8px;
  background: linear-gradient(135deg, #ff6f00, #ffca28); color: #fff;
  font-weight: 700; white-space: nowrap; cursor: help;
}
.curse-banner {
  text-align: center; font-size: 11px; font-weight: 600;
  padding: 3px 8px; margin-bottom: 4px; border-radius: 6px;
  background: linear-gradient(135deg, rgba(156,39,176,.12), rgba(233,30,99,.12));
  border: 1px solid rgba(156,39,176,.3); color: #7b1fa2;
}
.monster-hp {
  position: relative; flex: 1; min-width: 60px; height: 14px;
  background: #ffcdd2; border-radius: 7px; overflow: hidden;
}
.monster-hp-fill { height: 100%; background: #e53935; border-radius: 7px; transition: width .3s; }
.monster-hp span {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 9px; font-weight: bold; color: var(--theme-text-primary, #333);
}
.shop-wallet { font-size: 12px; color: var(--theme-warning, #ff9800); font-weight: 600; margin-left: auto; }

/* 怪物详情面板 */
.monster-detail-panel {
  margin-bottom: 4px; padding: 8px 10px; border-radius: 8px;
  background: var(--theme-bg-card, #fff); border: 1px solid rgba(229,57,53,.25);
  box-shadow: 0 2px 12px rgba(229,57,53,.1); font-size: 12px; position: relative; z-index: 20;
}
.monster-detail-panel .sdp-section { color: #e53935; }
.monster-detail-panel .ability-desc { color: #e65100; font-weight: 500; font-size: 11px; }

/* 被动行高亮 */
.passive-row b { color: #388e3c; }

/* 下一层预览 */
.next-zone { flex-direction: column; }
.next-floor-hint {
  display: flex; align-items: center; gap: 6px; width: 100%;
  padding: 5px 10px; border-radius: 8px; font-size: 12px;
  background: linear-gradient(135deg, rgba(102,126,234,.06), rgba(118,75,162,.06));
  border: 1px solid rgba(102,126,234,.2);
  color: var(--theme-text-secondary, #555);
}
.nfh-icon { font-size: 18px; }
.nfh-text { display: flex; flex-wrap: wrap; align-items: center; gap: 3px; }
.nfh-text b { font-weight: 700; }
.nfh-type-monster { color: #e53935; }
.nfh-type-boss { color: #d32f2f; }
.nfh-type-shop { color: #1565c0; }
.nfh-type-blessing { color: #7b1fa2; }
.nfh-type-chest { color: #ef6c00; }
.nfh-type-trap { color: #ff6f00; }
.nfh-type-random { color: #757575; }
.nfh-final { font-size: 10px; font-weight: 700; color: #d32f2f; }
.nfh-sub { font-size: 10px; color: var(--theme-text-tertiary, #999); }

/* ---- 背包 ---- */
.bp-section {
  margin-bottom: 4px; padding: 6px;
  background: var(--theme-bg-card, #fff); border-radius: 8px;
  border: 1px solid var(--theme-border-light, #eee);
}
.bp-header { display: flex; flex-direction: column; gap: 2px; margin-bottom: 4px; }
.bp-title-row { display: flex; align-items: center; justify-content: space-between; }
.bp-title { font-size: 12px; font-weight: bold; }
.bp-stat-tags { display: flex; flex-wrap: wrap; gap: 3px 6px; font-size: 10px; color: var(--theme-text-secondary, #888); }
.bp-stat-tags span { white-space: nowrap; }
.bp-expand-btn {
  padding: 1px 8px; border: 1px solid var(--theme-primary, #ff9800);
  border-radius: 10px; background: rgba(255,152,0,.08); color: var(--theme-primary, #ff9800);
  font-size: 10px; cursor: pointer; white-space: nowrap; line-height: 1.4;
}
.bp-expand-btn:hover { background: rgba(255,152,0,.18); }
.bp-expand-btn:disabled { opacity: .4; cursor: not-allowed; }
/* 套装/连锁/被动提示 */
.bp-bonus-bar { display: flex; flex-wrap: wrap; gap: 3px; margin-bottom: 4px; }
.bp-bonus-tag {
  font-size: 9px; padding: 1px 5px; border-radius: 8px; white-space: nowrap;
}
.bp-bonus-tag.set { background: rgba(255,152,0,.12); border: 1px solid rgba(255,152,0,.3); color: #f57c00; font-weight: 600; }
.bp-bonus-tag.chain { background: rgba(33,150,243,.1); border: 1px solid rgba(33,150,243,.3); color: #1976d2; }
.bp-bonus-tag.passive { background: rgba(76,175,80,.1); border: 1px solid rgba(76,175,80,.3); color: #388e3c; }
.bp-bonus-tag.passive.legendary { background: rgba(156,39,176,.1); border: 1px solid rgba(156,39,176,.35); color: #7b1fa2; font-weight: 600; }
.bp-grid-wrap {
  position: relative; margin: 0 auto;
  border: 2px solid var(--theme-border, #d0d0d0); border-radius: 4px;
  background: var(--theme-bg-secondary, #f0f0f0);
}
.bp-row { display: flex; }
.bp-cell {
  width: 36px; height: 36px;
  border: 1px solid var(--theme-border-light, #e0e0e0);
  box-sizing: border-box; position: relative;
}
.bp-cell-occ { background: rgba(100,100,255,.04); }
.bp-cell-target { background: rgba(76,175,80,.12); cursor: pointer; }
.cell-hint { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #43a047; pointer-events: none; }
.bp-item {
  position: absolute; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all .15s; z-index: 2;
  border: 2px solid transparent; box-sizing: border-box;
}
.bp-item:hover { transform: scale(1.04); z-index: 3; }
.bp-sel { z-index: 4; box-shadow: 0 0 0 2px #ff9800, 0 2px 6px rgba(255,152,0,.3); }
.bp-linked {
  z-index: 3;
  border: 2px solid rgba(124,77,255,.85) !important;
  box-shadow: 0 0 0 2px rgba(124,77,255,.7), 0 0 14px 2px rgba(124,77,255,.45), inset 0 0 8px rgba(124,77,255,.2);
  background: linear-gradient(135deg, rgba(124,77,255,.18), rgba(187,134,252,.12)) !important;
  animation: adj-pulse 1s ease-in-out infinite alternate;
}
@keyframes adj-pulse {
  from { box-shadow: 0 0 0 2px rgba(124,77,255,.6), 0 0 10px 1px rgba(124,77,255,.3), inset 0 0 6px rgba(124,77,255,.15); }
  to   { box-shadow: 0 0 0 3px rgba(124,77,255,.9), 0 0 20px 4px rgba(124,77,255,.5), inset 0 0 10px rgba(124,77,255,.25); }
}
.bp-item-icon { font-size: 18px; pointer-events: none; }
.bp-cons::after { content: '♻'; position: absolute; bottom: 0; right: 1px; font-size: 8px; opacity: .6; }
/* 附魔标记 */
.bp-ench-dot {
  position: absolute; top: -2px; right: -2px; width: 12px; height: 12px; border-radius: 50%;
  background: #7c4dff; color: #fff; font-size: 8px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; z-index: 5;
}
/* 诅咒物品 */
.bp-cursed { border-color: #b71c1c !important; }
.bp-cursed::before {
  content: '💀'; position: absolute; top: -3px; left: -3px; font-size: 9px; z-index: 5;
}
/* 附魔物品光效 */
.bp-enchanted { border-color: #7c4dff !important; }
/* 合成目标高亮 */
.bp-merge-target {
  z-index: 5;
  border: 2px solid #ff9800 !important;
  box-shadow: 0 0 0 2px rgba(255,152,0,.6), 0 0 12px rgba(255,152,0,.4);
  animation: merge-pulse 0.8s ease-in-out infinite alternate;
}
@keyframes merge-pulse {
  from { box-shadow: 0 0 0 2px rgba(255,152,0,.4), 0 0 8px rgba(255,152,0,.2); }
  to   { box-shadow: 0 0 0 3px rgba(255,152,0,.8), 0 0 16px rgba(255,152,0,.5); }
}
/* 特殊区域格 */
.bp-cell-bonus { background: rgba(255,215,0,.12) !important; }
.bp-cell-bonus::after {
  content: ''; position: absolute; inset: 2px; border: 1px dashed rgba(255,165,0,.35);
  border-radius: 2px; pointer-events: none;
}
.bonus-star { color: rgba(255,165,0,.5) !important; font-size: 9px !important; }
.bp-drag-ghost {
  position: absolute; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  z-index: 10; pointer-events: none; opacity: .75;
  border: 2px dashed var(--theme-primary, #ff9800); box-sizing: border-box;
  box-shadow: 0 4px 16px rgba(0,0,0,.25);
  transition: none;
}
.bp-drag-ghost.drag-merge {
  border: 2px solid #ff9800; opacity: .9;
  box-shadow: 0 0 16px rgba(255,152,0,.6);
}
.drag-merge-icon {
  position: absolute; top: -6px; right: -6px;
  font-size: 12px; line-height: 1;
  background: #ff9800; border-radius: 50%; padding: 2px;
  box-shadow: 0 1px 4px rgba(0,0,0,.3);
}
.bp-item.rarity-common { background: rgba(158,158,158,.15); border-color: #bdbdbd; }
.bp-item.rarity-uncommon { background: rgba(76,175,80,.12); border-color: #66bb6a; }
.bp-item.rarity-rare { background: rgba(33,150,243,.12); border-color: #42a5f5; }
.bp-item.rarity-legendary {
  background: linear-gradient(135deg, rgba(255,152,0,.15), rgba(255,193,7,.2));
  border-color: #ffa726; animation: lglow 2s ease-in-out infinite alternate;
}
@keyframes lglow { from { box-shadow: 0 0 3px rgba(255,152,0,.3) } to { box-shadow: 0 0 8px rgba(255,152,0,.5) } }
.bp-item.rarity-mythic {
  background: linear-gradient(135deg, rgba(156,39,176,.18), rgba(233,30,99,.15));
  border-color: #ab47bc; animation: mglow 2s ease-in-out infinite alternate;
}
@keyframes mglow { from { box-shadow: 0 0 4px rgba(156,39,176,.4) } to { box-shadow: 0 0 10px rgba(233,30,99,.5) } }
.bp-item.rarity-eternal {
  background: linear-gradient(135deg, rgba(255,215,0,.2), rgba(255,69,0,.12));
  border-color: #ffd700; animation: eglow 1.5s ease-in-out infinite alternate;
}
@keyframes eglow { from { box-shadow: 0 0 5px rgba(255,215,0,.5) } to { box-shadow: 0 0 14px rgba(255,69,0,.6) } }

/* 物品操作条 */
.bp-toolbar {
  margin-top: 4px; padding: 6px 8px; border-radius: 6px;
  background: var(--theme-bg-secondary, #f5f5f5); border: 1px solid var(--theme-border, #ddd);
  display: flex; flex-direction: column; gap: 4px;
}
.bp-tb-info {
  display: flex; flex-wrap: wrap; gap: 3px 6px; align-items: center; font-size: 11px;
}
.bp-tb-name { font-size: 12px; font-weight: bold; }
.rt-common { color: #757575; } .rt-uncommon { color: #43a047; } .rt-rare { color: #1e88e5; } .rt-legendary { color: #f57c00; } .rt-mythic { color: #9c27b0; } .rt-eternal { color: #ff6f00; text-shadow: 0 0 4px rgba(255,215,0,.5); }
.bp-tb-desc { color: var(--theme-text-secondary, #666); }
.bp-tb-adj { font-size: 10px; color: var(--theme-purple, #7c4dff); }
.bp-tb-curse { font-size: 10px; color: #b71c1c; font-weight: 600; }
.bp-tb-purified { font-size: 10px; color: #7c4dff; font-weight: 600; }
.bp-tb-passive { font-size: 10px; color: #43a047; font-weight: 500; }
.ench-tag {
  font-size: 9px; padding: 1px 4px; border-radius: 4px;
  background: rgba(124,77,255,.1); border: 1px solid rgba(124,77,255,.3);
  color: #7c4dff; white-space: nowrap;
}
.bp-tb-btns { display: flex; gap: 3px; flex-wrap: wrap; }
.tb-btn {
  padding: 3px 6px; border: none; border-radius: 4px;
  font-size: 11px; font-weight: 600; cursor: pointer; white-space: nowrap;
}
.tb-btn.use { background: #43a047; color: #fff; }
.tb-btn.move { background: #1565c0; color: #fff; }
.tb-btn.rotate { background: #7c4dff; color: #fff; }
.tb-btn.discard { background: #ef5350; color: #fff; }
.tb-btn.sell { background: #ff9800; color: #fff; }
.tb-btn.enchant { background: #7c4dff; color: #fff; }
.tb-btn.enchant:disabled { opacity: .4; cursor: not-allowed; }
.tb-btn.merge { background: #f57c00; color: #fff; }
.tb-btn.cancel { background: var(--theme-border, #bbb); color: #333; margin-left: 6px; }
.bp-move-hint {
  margin-top: 4px; padding: 4px 8px; border-radius: 4px;
  background: rgba(21,101,192,.08); color: #1565c0;
  font-size: 12px; display: flex; align-items: center; gap: 4px;
}

/* ---- 操作区 ---- */
.action-zone {
  display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 4px;
}
.act-btn {
  flex: 1; min-width: 60px; padding: 8px 4px; border: none; border-radius: 8px;
  font-size: 13px; font-weight: bold; cursor: pointer; color: #fff; text-align: center;
}
.act-btn:disabled { opacity: .4; cursor: not-allowed; }
.act-btn.fight { background: #e53935; }
.act-btn.flee { background: #757575; }
.act-btn.chest { background: #ff9800; }
.act-btn.disarm { background: #ff5722; }
.act-btn.bypass { background: #9e9e9e; }
.act-btn.skip { background: #757575; }
.act-btn.next { background: linear-gradient(135deg, #667eea, #764ba2); }
.act-btn.reroll { background: linear-gradient(135deg, #f093fb, #f5576c); flex: none; width: 100%; font-size: 12px; padding: 6px 10px; margin-top: 4px; }
.act-btn.reroll:disabled { opacity: .4; cursor: not-allowed; }

/* 商店物品 */
.shop-items { display: flex; gap: 6px; flex-wrap: wrap; width: 100%; }
.shop-card {
  flex: 1; min-width: 70px; max-width: 110px;
  padding: 6px; border-radius: 8px; text-align: center; cursor: pointer;
  border: 2px solid var(--theme-border, #e0e0e0);
  background: var(--theme-bg-secondary, #fafafa); transition: all .2s;
}
.shop-card:hover { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,.1); }
.shop-card.shop-disabled { opacity: .5; cursor: not-allowed; }
.shop-card.shop-disabled:hover { transform: none; box-shadow: none; }
.shop-card.rarity-common { border-color: #9e9e9e; }
.shop-card.rarity-uncommon { border-color: #4caf50; }
.shop-card.rarity-rare { border-color: #2196f3; }
.shop-card.rarity-legendary { border-color: #ff9800; background: linear-gradient(135deg, rgba(255,152,0,.05), rgba(255,193,7,.08)); }
.shop-card.rarity-mythic { border-color: #ab47bc; background: linear-gradient(135deg, rgba(156,39,176,.06), rgba(233,30,99,.06)); }
.shop-card.rarity-eternal { border-color: #ffd700; background: linear-gradient(135deg, rgba(255,215,0,.08), rgba(255,69,0,.05)); }
.si-icon { font-size: 22px; display: block; }
.si-name { font-size: 12px; font-weight: bold; }
.si-tag {
  font-size: 9px; padding: 0px 4px; border-radius: 6px; display: inline-block; margin: 1px 0;
}
.si-tag.cursed { background: rgba(183,28,28,.1); color: #b71c1c; border: 1px solid rgba(183,28,28,.25); }
.si-tag.passive { background: rgba(76,175,80,.1); color: #388e3c; border: 1px solid rgba(76,175,80,.25); }
.si-info { font-size: 10px; color: var(--theme-text-secondary, #888); display: block; }
.si-price { font-size: 11px; font-weight: bold; color: #1565c0; }
.si-price.disabled { color: #bbb; }

/* 祝福选择 */
.blessing-list { display: flex; flex-wrap: wrap; gap: 6px; width: 100%; }
.bless-btn {
  flex: 1; min-width: 80px; display: flex; flex-direction: column; align-items: center;
  padding: 6px 8px; text-align: center;
  border: 2px solid var(--theme-border, #e8e8e8); border-radius: 8px;
  background: var(--theme-bg-secondary, #fafafa); cursor: pointer; transition: all .2s;
}
.bless-btn:hover {
  transform: translateY(-1px); box-shadow: 0 2px 6px rgba(0,0,0,.1);
}
.bless-btn b { font-size: 12px; }
.bless-btn span { font-size: 10px; color: var(--theme-text-tertiary, #888); line-height: 1.3; }
/* 祝福稀有度颜色 */
.bless-common { border-color: #bdbdbd; }
.bless-common b { color: #757575; }
.bless-common:hover { border-color: #9e9e9e; background: rgba(158,158,158,.08); }
.bless-rare { border-color: #42a5f5; background: rgba(33,150,243,.04); }
.bless-rare b { color: #1976d2; }
.bless-rare:hover { border-color: #1e88e5; background: rgba(33,150,243,.1); box-shadow: 0 2px 8px rgba(33,150,243,.15); }
.bless-epic { border-color: #ab47bc; background: rgba(156,39,176,.04); }
.bless-epic b { color: #8e24aa; }
.bless-epic:hover { border-color: #9c27b0; background: rgba(156,39,176,.1); box-shadow: 0 2px 8px rgba(156,39,176,.18); }
.bless-legendary {
  border-color: #ffa726;
  background: linear-gradient(135deg, rgba(255,152,0,.06), rgba(255,193,7,.1));
  animation: bless-glow 2s ease-in-out infinite alternate;
}
.bless-legendary b { color: #e65100; }
.bless-legendary:hover {
  border-color: #ff9800; background: linear-gradient(135deg, rgba(255,152,0,.12), rgba(255,193,7,.18));
  box-shadow: 0 2px 10px rgba(255,152,0,.25);
}
@keyframes bless-glow {
  from { box-shadow: 0 0 4px rgba(255,152,0,.15); }
  to   { box-shadow: 0 0 10px rgba(255,152,0,.3); }
}

/* 撤退 */
.retreat-btn {
  display: block; width: 100%; padding: 5px 0; margin-bottom: 4px;
  border: 1px solid var(--theme-warning, #ff9800); border-radius: 6px;
  background: transparent; color: var(--theme-warning, #ff9800);
  font-size: 12px; cursor: pointer; text-align: center;
}
.retreat-btn:hover { background: rgba(255,152,0,.1); }
.retreat-btn.confirming {
  border-color: #e53935; color: #e53935; background: rgba(229,57,53,.08);
  animation: pulse .8s ease-in-out infinite alternate;
}
.retreat-btn.confirming:hover { background: rgba(229,57,53,.18); }

/* 结果 */
.game-result { text-align: center; padding: 10px; border-radius: 8px; margin-top: 4px; }
.game-result.win { background: var(--theme-success-bg, linear-gradient(135deg, #e8f5e9, #c8e6c9)); }
.game-result.lose { background: var(--theme-error-bg, linear-gradient(135deg, #ffebee, #ffcdd2)); }
.result-title { font-size: 16px; font-weight: bold; }
.win .result-title { color: var(--theme-success, #2e7d32); }
.lose .result-title { color: var(--theme-error, #c62828); }
.result-detail { font-size: 13px; margin-top: 2px; }
.win .result-detail { color: var(--theme-success, #388e3c); }
.lose .result-detail { color: var(--theme-error-light, #e57373); }
.result-exp { font-size: 13px; margin-top: 2px; color: var(--theme-success, #388e3c); }
.result-exp.lost { color: var(--theme-text-tertiary, #999); }

/* 移动端点击提示气泡 */
.tap-tip {
  position: fixed; bottom: 60px; left: 50%; transform: translateX(-50%);
  max-width: 85vw; padding: 8px 14px; border-radius: 10px;
  background: rgba(30, 30, 30, .92); color: #fff; font-size: 13px; line-height: 1.5;
  box-shadow: 0 4px 16px rgba(0,0,0,.3); z-index: 9999;
  text-align: center; word-break: break-word;
  pointer-events: auto; cursor: pointer;
}
.tip-fade-enter-active { transition: all .2s ease-out; }
.tip-fade-leave-active { transition: all .15s ease-in; }
.tip-fade-enter-from { opacity: 0; transform: translateX(-50%) translateY(8px); }
.tip-fade-leave-to { opacity: 0; transform: translateX(-50%) translateY(4px); }
</style>