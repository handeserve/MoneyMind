<template>
  <el-container class="app-container">
    <el-aside width="200px">
      <div class="logo">
        <h1>MoneyMind</h1>
      </div>
      <el-menu
        router
        :default-active="$route.path"
        class="el-menu-vertical"
      >
        <el-menu-item index="/financial-overview">
          <el-icon><data-analysis /></el-icon>
          <span>财务概览</span>
        </el-menu-item>
        <el-menu-item index="/expenses">
          <el-icon><document /></el-icon>
          <span>支出记录</span>
        </el-menu-item>
        <el-menu-item index="/import">
          <el-icon><upload /></el-icon>
          <span>数据导入</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>

      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header>
        <div class="header-content">
          <h2>{{ $route.meta.title }}</h2>
        </div>
      </el-header>
      
      <el-main>
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { DataAnalysis, Document, Upload, Setting } from '@element-plus/icons-vue'
console.log('App.vue 已加载')
</script>

<style>
.app-container {
  height: 100vh;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #409EFF;
  color: white;
}

.logo h1 {
  margin: 0;
  font-size: 1.5em;
}

.el-aside {
  background-color: #304156;
  color: white;
}

.el-menu {
  border-right: none;
}

.el-header {
  background-color: white;
  border-bottom: 1px solid #dcdfe6;
  padding: 0 20px;
}

.header-content {
  height: 100%;
  display: flex;
  align-items: center;
}

.header-content h2 {
  margin: 0;
  font-size: 1.2em;
  color: #303133;
}

.el-main {
  background-color: #f0f2f5;
  padding: 20px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style> 