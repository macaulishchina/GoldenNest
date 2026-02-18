<template>
  <div class="guest-home">
    <div class="hero-section">
      <div class="hero-content">
        <div class="logo-large">
          <span class="logo-icon">🏠</span>
          <h1 class="app-title">小金库</h1>
        </div>
        <p class="tagline">Golden Nest · 家庭财富共创计划</p>
        <p class="description">
          全新的家庭财富管理模式，让每一笔存款都成为家庭股权，
          时间加权复利机制激励早期投入，共同见证家庭资产增长
        </p>
        
        <div class="cta-buttons">
          <n-button type="primary" size="large" @click="goToRegister" class="cta-button">
            立即注册 🚀
          </n-button>
          <n-button size="large" @click="goToLogin" class="cta-button-secondary">
            已有账号，去登录
          </n-button>
        </div>
      </div>
    </div>
    
    <div class="features-section">
      <h2 class="section-title">✨ 核心特色</h2>
      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">📊</div>
          <h3 class="feature-title">股权化管理</h3>
          <p class="feature-desc">
            每笔存款自动转化为家庭股权，按加权金额计算股权占比，
            公平透明，让每个成员都是家庭资产的股东
          </p>
        </div>
        
        <div class="feature-card">
          <div class="feature-icon">⏰</div>
          <h3 class="feature-title">时间加权复利</h3>
          <p class="feature-desc">
            存款时间越早，权重越高。默认3%年复利激励早期投入，
            让时间成为财富增长的朋友
          </p>
        </div>
        
        <div class="feature-card">
          <div class="feature-icon">🤝</div>
          <h3 class="feature-title">家庭协作</h3>
          <p class="feature-desc">
            支出审批、股东投票、股权赠与等功能，
            让家庭决策更民主，财务管理更透明
          </p>
        </div>
        
        <div class="feature-card">
          <div class="feature-icon">📈</div>
          <h3 class="feature-title">理财投资</h3>
          <p class="feature-desc">
            统一管理家庭理财产品，收益按股权比例分配，
            让每个成员分享家庭资产增值
          </p>
        </div>
        
        <div class="feature-card">
          <div class="feature-icon">🎯</div>
          <h3 class="feature-title">目标储蓄</h3>
          <p class="feature-desc">
            设定家庭储蓄目标，可视化追踪进度，
            激励全家共同为目标努力
          </p>
        </div>
        
        <div class="feature-card">
          <div class="feature-icon">🎮</div>
          <h3 class="feature-title">游戏化体验</h3>
          <p class="feature-desc">
            家庭宠物、成就系统、家庭赌注等趣味功能，
            让财务管理不再枯燥
          </p>
        </div>
      </div>
    </div>
    
    <div class="demo-section">
      <h2 class="section-title">🎬 预览应用</h2>
      <p class="demo-hint">点击右上角菜单，浏览应用的完整功能框架</p>
      <n-alert type="info" class="demo-alert">
        <template #icon>
          <n-icon><InformationCircleOutline /></n-icon>
        </template>
        您当前处于<strong>游客模式</strong>，可以浏览应用界面，但功能受限。
        在仪表盘可以查看示例数据演示。
        <strong>注册账号后</strong>可使用完整功能！
      </n-alert>
      
      <div class="demo-actions">
        <n-button type="primary" @click="goToDashboard">
          查看仪表盘演示 →
        </n-button>
      </div>
    </div>
    
    <div class="cta-section">
      <h2 class="cta-title">准备好开始了吗？</h2>
      <p class="cta-text">
        立即注册，创建您的家庭账户，开启财富共创之旅
      </p>
      <div class="cta-buttons">
        <n-button type="primary" size="large" @click="goToRegister" class="cta-button">
          免费注册 🎉
        </n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { InformationCircleOutline } from '@vicons/ionicons5'

const router = useRouter()

function goToRegister() {
  router.push('/register')
}

function goToLogin() {
  router.push('/login')
}

function goToDashboard() {
  router.push('/')
}
</script>

<style scoped>
.guest-home {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.hero-section {
  padding: 80px 20px;
  text-align: center;
  color: white;
}

.hero-content {
  max-width: 800px;
  margin: 0 auto;
}

.logo-large {
  margin-bottom: 24px;
}

.logo-icon {
  font-size: 80px;
  display: block;
  margin-bottom: 16px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.app-title {
  font-size: 48px;
  font-weight: 700;
  margin: 0;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
}

.tagline {
  font-size: 20px;
  margin: 16px 0;
  opacity: 0.95;
}

.description {
  font-size: 18px;
  line-height: 1.8;
  margin: 32px 0;
  opacity: 0.9;
}

.cta-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 40px;
}

.cta-button {
  min-width: 180px;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
}

.cta-button-secondary {
  min-width: 180px;
  height: 48px;
  font-size: 16px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.5);
}

.cta-button-secondary:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.8);
}

.features-section {
  padding: 80px 20px;
  background: white;
}

.section-title {
  text-align: center;
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 48px;
  color: #333;
}

.features-grid {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 32px;
}

.feature-card {
  padding: 32px;
  background: #f8f9fa;
  border-radius: 16px;
  transition: all 0.3s;
}

.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
}

.feature-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.feature-title {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #333;
}

.feature-desc {
  font-size: 15px;
  line-height: 1.6;
  color: #666;
}

.demo-section {
  padding: 80px 20px;
  background: #f8f9fa;
  text-align: center;
}

.demo-hint {
  font-size: 16px;
  color: #666;
  margin-bottom: 32px;
}

.demo-alert {
  max-width: 800px;
  margin: 0 auto 32px;
  text-align: left;
}

.demo-actions {
  margin-top: 32px;
}

.cta-section {
  padding: 80px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  text-align: center;
  color: white;
}

.cta-title {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 16px;
}

.cta-text {
  font-size: 18px;
  margin-bottom: 32px;
  opacity: 0.95;
}

@media (max-width: 768px) {
  .hero-section {
    padding: 60px 16px;
  }
  
  .logo-icon {
    font-size: 60px;
  }
  
  .app-title {
    font-size: 36px;
  }
  
  .tagline {
    font-size: 16px;
  }
  
  .description {
    font-size: 16px;
  }
  
  .section-title {
    font-size: 28px;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
    gap: 24px;
  }
  
  .cta-buttons {
    flex-direction: column;
    align-items: center;
  }
  
  .cta-button,
  .cta-button-secondary {
    width: 100%;
    max-width: 300px;
  }
}
</style>
