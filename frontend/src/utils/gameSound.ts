/**
 * 游戏音效工具 - 使用 Web Audio API 生成简单音效
 * 无需外部音频文件，纯代码生成
 */

let audioCtx: AudioContext | null = null

function getCtx(): AudioContext | null {
  if (!audioCtx) {
    try {
      audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
    } catch {
      return null
    }
  }
  // 每次调用都尝试 resume —— 在用户手势内调用时浏览器会立即恢复
  if (audioCtx.state === 'suspended') {
    audioCtx.resume()
  }
  // 不再跳过播放：即使 resume 尚在进行中，oscillator 也会排队等待恢复后播放
  return audioCtx
}

/**
 * 预热 AudioContext —— 在任意用户交互(click/touchend)时调用
 * 播放一个静音缓冲区来解锁 iOS Safari 的音频策略
 */
export function warmUp() {
  if (!audioCtx) {
    try {
      audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
    } catch { return }
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume()
  }
  // iOS Safari 需要在用户手势中实际播放一个音频缓冲区来完全解锁
  try {
    const buf = audioCtx.createBuffer(1, 1, 22050)
    const src = audioCtx.createBufferSource()
    src.buffer = buf
    src.connect(audioCtx.destination)
    src.start(0)
  } catch { /* ignore */ }
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

// ============ 探险背景音乐 (程序生成) ============

/**
 * 用 Web Audio API 生成循环的地牢氛围背景音乐
 * - 柔和和弦 pad（Am → F → C → G 循环）
 * - 轻柔的琶音点缀
 * - 低沉的低音线
 * - 自动循环，调用 stop() 淡出停止
 */
class AdventureBGM {
  private running = false
  private masterGain: GainNode | null = null
  private timers: ReturnType<typeof setTimeout>[] = []
  private sources: (OscillatorNode | AudioBufferSourceNode)[] = []
  private loopTimer: ReturnType<typeof setTimeout> | null = null
  private _volume = 0.25

  /** 和弦进行：Am → F → C → G，每个和弦的根音 + 三度 + 五度 */
  private chords = [
    [220, 261.63, 329.63],   // Am: A3 C4 E4
    [174.61, 220, 261.63],   // F:  F3 A3 C4
    [261.63, 329.63, 392],   // C:  C4 E4 G4
    [196, 246.94, 293.66],   // G:  G3 B3 D4
  ]

  /** 琶音音符池（五声音阶风格）*/
  private arpNotes = [329.63, 392, 440, 523.25, 587.33, 659.25, 783.99]

  get volume() { return this._volume }
  set volume(v: number) {
    this._volume = Math.max(0, Math.min(1, v))
    if (this.masterGain && this.running) {
      const ctx = getCtx()
      if (ctx) this.masterGain.gain.setTargetAtTime(this._volume, ctx.currentTime, 0.1)
    }
  }

  start() {
    if (this.running) return
    if (muted) return
    const ctx = getCtx()
    if (!ctx) return

    this.running = true
    this.masterGain = ctx.createGain()
    // 淡入
    this.masterGain.gain.setValueAtTime(0, ctx.currentTime)
    this.masterGain.gain.linearRampToValueAtTime(this._volume, ctx.currentTime + 1.5)
    this.masterGain.connect(ctx.destination)

    this.scheduleLoop(ctx)
  }

  stop() {
    if (!this.running) return
    this.running = false
    // 清除未来的定时器
    this.timers.forEach(t => clearTimeout(t))
    this.timers = []
    if (this.loopTimer) { clearTimeout(this.loopTimer); this.loopTimer = null }

    // 淡出
    const ctx = getCtx()
    if (ctx && this.masterGain) {
      const now = ctx.currentTime
      this.masterGain.gain.cancelScheduledValues(now)
      this.masterGain.gain.setValueAtTime(this.masterGain.gain.value, now)
      this.masterGain.gain.linearRampToValueAtTime(0, now + 0.8)
      // 延迟后断开并清理
      setTimeout(() => {
        this.sources.forEach(s => { try { s.stop() } catch { /* ok */ } })
        this.sources = []
        try { this.masterGain?.disconnect() } catch { /* ok */ }
        this.masterGain = null
      }, 1000)
    } else {
      this.sources.forEach(s => { try { s.stop() } catch { /* ok */ } })
      this.sources = []
      this.masterGain = null
    }
  }

  /** 是否正在播放 */
  get isPlaying() { return this.running }

  private scheduleLoop(ctx: AudioContext) {
    if (!this.running) return

    const chordDur = 2.4    // 每个和弦持续秒数
    const loopDur = chordDur * this.chords.length // 整个循环 ~9.6s

    // ---- 和弦 Pad ----
    this.chords.forEach((chord, ci) => {
      const startDelay = ci * chordDur * 1000
      const t = this.delay(() => {
        if (!this.running || !this.masterGain) return
        chord.forEach(freq => {
          this.playPad(ctx, freq, chordDur, 0.06)
        })
      }, startDelay)
      this.timers.push(t)
    })

    // ---- 低音线 ----
    const bassNotes = [110, 87.31, 130.81, 98]  // Am bass, F bass, C bass, G bass
    bassNotes.forEach((freq, i) => {
      const t = this.delay(() => {
        if (!this.running || !this.masterGain) return
        this.playBass(ctx, freq, chordDur * 0.9, 0.07)
      }, i * chordDur * 1000)
      this.timers.push(t)
    })

    // ---- 琶音点缀 ----
    const arpCount = 6 + Math.floor(Math.random() * 4)
    for (let i = 0; i < arpCount; i++) {
      const time = Math.random() * loopDur * 1000
      const note = this.arpNotes[Math.floor(Math.random() * this.arpNotes.length)]
      const t = this.delay(() => {
        if (!this.running || !this.masterGain) return
        this.playArp(ctx, note, 0.3 + Math.random() * 0.4, 0.02 + Math.random() * 0.02)
      }, time)
      this.timers.push(t)
    }

    // ---- 下一个循环 ----
    this.loopTimer = this.delay(() => {
      this.timers = []
      this.scheduleLoop(ctx)
    }, loopDur * 1000)
  }

  private playPad(ctx: AudioContext, freq: number, dur: number, vol: number) {
    try {
      if (!this.masterGain) return
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.setValueAtTime(freq, ctx.currentTime)
      // 柔和包络
      gain.gain.setValueAtTime(0, ctx.currentTime)
      gain.gain.linearRampToValueAtTime(vol, ctx.currentTime + 0.4)
      gain.gain.setValueAtTime(vol, ctx.currentTime + dur - 0.5)
      gain.gain.linearRampToValueAtTime(0, ctx.currentTime + dur)
      osc.connect(gain)
      gain.connect(this.masterGain)
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + dur)
      this.sources.push(osc)
      // 自动清理引用
      osc.onended = () => {
        const idx = this.sources.indexOf(osc)
        if (idx >= 0) this.sources.splice(idx, 1)
      }
    } catch { /* ok */ }
  }

  private playBass(ctx: AudioContext, freq: number, dur: number, vol: number) {
    try {
      if (!this.masterGain) return
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'triangle'
      osc.frequency.setValueAtTime(freq, ctx.currentTime)
      gain.gain.setValueAtTime(0, ctx.currentTime)
      gain.gain.linearRampToValueAtTime(vol, ctx.currentTime + 0.2)
      gain.gain.setValueAtTime(vol, ctx.currentTime + dur - 0.3)
      gain.gain.linearRampToValueAtTime(0, ctx.currentTime + dur)
      osc.connect(gain)
      gain.connect(this.masterGain)
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + dur)
      this.sources.push(osc)
      osc.onended = () => {
        const idx = this.sources.indexOf(osc)
        if (idx >= 0) this.sources.splice(idx, 1)
      }
    } catch { /* ok */ }
  }

  private playArp(ctx: AudioContext, freq: number, dur: number, vol: number) {
    try {
      if (!this.masterGain) return
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.setValueAtTime(freq, ctx.currentTime)
      // 短促明亮音
      gain.gain.setValueAtTime(vol, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur)
      osc.connect(gain)
      gain.connect(this.masterGain)
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + dur)
      this.sources.push(osc)
      osc.onended = () => {
        const idx = this.sources.indexOf(osc)
        if (idx >= 0) this.sources.splice(idx, 1)
      }
    } catch { /* ok */ }
  }

  private delay(fn: () => void, ms: number): ReturnType<typeof setTimeout> {
    return setTimeout(fn, ms)
  }
}

export const adventureBGM = new AdventureBGM()

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
