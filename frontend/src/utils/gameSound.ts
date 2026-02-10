/**
 * 游戏音效工具 - 使用 Web Audio API 生成简单音效
 * 无需外部音频文件，纯代码生成
 */

let audioCtx: AudioContext | null = null
let ctxReady = false

function getCtx(): AudioContext | null {
  if (!audioCtx) {
    try {
      audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
    } catch {
      return null
    }
  }
  // resume if suspended (autoplay policy)
  if (audioCtx.state === 'suspended') {
    audioCtx.resume().then(() => { ctxReady = true })
    // 首次 resume 尚未完成时返回 null，跳过本次播放
    if (!ctxReady) return null
  } else {
    ctxReady = true
  }
  return audioCtx
}

/**
 * 预热 AudioContext —— 在任意用户交互时调用一次
 * 确保后续播放不会因为 resume 延迟而被截断
 */
export function warmUp() {
  if (!audioCtx) {
    try {
      audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
    } catch { return }
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume().then(() => { ctxReady = true })
  } else {
    ctxReady = true
  }
}

/** 是否静音 */
let muted = false
export function setMuted(v: boolean) { muted = v }
export function isMuted() { return muted }
export function toggleMute() { muted = !muted; return muted }

function playTone(
  freq: number,
  duration: number,
  type: OscillatorType = 'sine',
  volume = 0.3,
  ramp?: { freq?: number; vol?: number },
) {
  if (muted) return
  try {
    const ctx = getCtx()
    if (!ctx) return
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = type
    osc.frequency.setValueAtTime(freq, ctx.currentTime)
    gain.gain.setValueAtTime(volume, ctx.currentTime)

    if (ramp?.freq) {
      osc.frequency.linearRampToValueAtTime(ramp.freq, ctx.currentTime + duration)
    }
    // fade out to avoid click
    gain.gain.linearRampToValueAtTime(ramp?.vol ?? 0, ctx.currentTime + duration)

    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + duration)
  } catch {
    // silently fail
  }
}

function playNoise(duration: number, volume = 0.15) {
  if (muted) return
  try {
    const ctx = getCtx()
    if (!ctx) return
    const bufferSize = ctx.sampleRate * duration
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate)
    const data = buffer.getChannelData(0)
    for (let i = 0; i < bufferSize; i++) {
      data[i] = (Math.random() * 2 - 1) * Math.max(0, 1 - i / bufferSize)
    }
    const source = ctx.createBufferSource()
    source.buffer = buffer
    const gain = ctx.createGain()
    gain.gain.setValueAtTime(volume, ctx.currentTime)
    gain.gain.linearRampToValueAtTime(0, ctx.currentTime + duration)
    source.connect(gain)
    gain.connect(ctx.destination)
    source.start()
  } catch {
    // silently fail
  }
}

// ============ 扫雷音效 ============
export const mineSound = {
  /** 翻开安全格子 */
  reveal() {
    playTone(600, 0.15, 'sine', 0.18)
  },
  /** 翻开一大片空白 */
  revealMany() {
    playTone(500, 0.2, 'sine', 0.15)
    setTimeout(() => playTone(700, 0.18, 'sine', 0.15), 80)
  },
  /** 插旗 */
  flag() {
    playTone(800, 0.15, 'triangle', 0.22)
  },
  /** 取消旗 */
  unflag() {
    playTone(400, 0.15, 'triangle', 0.18)
  },
  /** 和弦成功 */
  chord() {
    playTone(520, 0.15, 'sine', 0.18)
    setTimeout(() => playTone(660, 0.15, 'sine', 0.18), 70)
    setTimeout(() => playTone(780, 0.18, 'sine', 0.18), 140)
  },
  /** 踩雷 */
  explode() {
    playNoise(0.5, 0.28)
    playTone(200, 0.4, 'sawtooth', 0.18, { freq: 60 })
  },
  /** 胜利 */
  win() {
    const notes = [523, 659, 784, 1047]
    notes.forEach((f, i) => {
      setTimeout(() => playTone(f, 0.25, 'sine', 0.18), i * 130)
    })
  },
}

// ============ 记忆翻牌音效 ============
export const memorySound = {
  /** 翻牌 */
  flip() {
    playTone(440, 0.15, 'sine', 0.18)
  },
  /** 配对成功 */
  match() {
    playTone(523, 0.15, 'sine', 0.2)
    setTimeout(() => playTone(784, 0.2, 'sine', 0.2), 100)
  },
  /** 配对失败 */
  mismatch() {
    playTone(300, 0.2, 'triangle', 0.15)
    setTimeout(() => playTone(250, 0.2, 'triangle', 0.15), 120)
  },
  /** 胜利 */
  win() {
    const notes = [523, 587, 659, 784, 1047]
    notes.forEach((f, i) => {
      setTimeout(() => playTone(f, 0.25, 'sine', 0.18), i * 110)
    })
  },
}

// ============ 探险音效 ============
export const adventureSound = {
  /** 进入下一层 */
  nextFloor() {
    playTone(400, 0.18, 'sine', 0.15)
    setTimeout(() => playTone(500, 0.18, 'sine', 0.15), 100)
  },
  /** 攻击 */
  attack() {
    playTone(300, 0.15, 'sawtooth', 0.12, { freq: 500 })
  },
  /** 受伤 */
  hurt() {
    playTone(250, 0.18, 'square', 0.12, { freq: 180 })
  },
  /** 获得宝箱 */
  chest() {
    playTone(600, 0.15, 'sine', 0.18)
    setTimeout(() => playTone(800, 0.2, 'sine', 0.18), 100)
  },
  /** 商店 */
  shop() {
    playTone(500, 0.15, 'sine', 0.12)
    setTimeout(() => playTone(600, 0.15, 'sine', 0.12), 120)
    setTimeout(() => playTone(700, 0.15, 'sine', 0.12), 240)
  },
  /** 获得增益 */
  buff() {
    playTone(523, 0.18, 'sine', 0.18)
    setTimeout(() => playTone(659, 0.18, 'sine', 0.18), 120)
    setTimeout(() => playTone(784, 0.2, 'sine', 0.2), 240)
  },
}

// ============ 炒股音效 ============
export const stockSound = {
  /** 买入 */
  buy() {
    playTone(500, 0.15, 'sine', 0.15)
    setTimeout(() => playTone(600, 0.15, 'sine', 0.15), 80)
  },
  /** 卖出 */
  sell() {
    playTone(600, 0.15, 'sine', 0.15)
    setTimeout(() => playTone(500, 0.15, 'sine', 0.15), 80)
  },
  /** 持有/下一回合 */
  hold() {
    playTone(440, 0.15, 'sine', 0.1)
  },
}
