<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-left">
        <router-link to="/">
          <el-button type="info" :icon="ArrowLeft">返回</el-button>
        </router-link>
      </div>

      <div class="header-right">
        <el-button
            type="warning"
            :icon="RefreshLeft"
            @click="handleRestart"
            class="restart-button">
        </el-button>
        <el-select
            v-model="currentVoice"
            @change="setVoiceType"
            class="voice-selector">
          <el-option
              v-for="voice in availableVoices"
              :key="voice.id"
              :label="voice.name"
              :value="voice.id"/>
        </el-select>
      </div>
    </el-header>

    <el-main class="app-main">
      <div class="message-list" ref="messageList">
        <div v-for="message in messages"
             :key="message.id"
             :class="['message-wrapper', message.isUser ? 'user-message' : 'ai-message']">
          <div class="message">
            <div class="message-avatar">
              <el-avatar :size="40" :src="message.isUser ? userAvatar : aiAvatar"/>
            </div>
            <div class="message-content">
              <div class="message-audio" v-if="message.audioData">
                <el-button
                    class="play-button"
                    :icon="VideoPlay"
                    @click="playAudio(message.audioData)"
                />
              </div>
              <transition name="slide-fade">
                <div class="message-text" v-show="message.showText">{{ message.content }}</div>
              </transition>
              <div class="message-actions">
                <el-button
                    v-if="message.audioData"
                    size="small"
                    link
                    type="primary"
                    @click="message.showText = !message.showText">
                  {{ message.showText ? '隐藏文字' : '显示文字' }}
                </el-button>
              </div>
              <div class="message-status" v-if="message.isUser">
                {{
                  message.status === 'sending' ? '发送中...' :
                      message.status === 'error' ? '发送失败' : ''
                }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-main>

    <el-footer class="app-footer">
      <div class="voice-input">
        <el-button
            :type="isRecording ? 'warning' : 'success'"
            size="large"
            :icon="isRecording ? Loading : Microphone"
            @click="toggleRecording">
          {{ isRecording ? '点击结束' : '点击录音' }}
        </el-button>
      </div>
    </el-footer>
  </el-container>
</template>

<script setup lang="ts">
import {onMounted, onUnmounted, ref, watch} from 'vue'
import {ArrowLeft, Loading, Microphone, RefreshLeft, VideoPlay} from "@element-plus/icons-vue"
import {useVoiceChat} from '@/composables/useVoiceChat'

const userAvatar = '/user.png'
const aiAvatar = '/qwen.png'
const messageList = ref<HTMLElement | null>(null)

const {
  messages,
  isRecording,
  startRecording,
  stopRecording,
  playAudio,
  cleanup,
  currentVoice,
  availableVoices,
  setVoiceType,
  restartChat
} = useVoiceChat({
  onMessageStatusChange: (messageId, status) => {
    console.debug('[VoiceChat] Message status changed:', messageId, status)
  }
})

const toggleRecording = () => {
  if (isRecording.value) {
    stopRecording()
  } else {
    startRecording()
  }
}

const scrollToBottom = () => {
  if (messageList.value) {
    setTimeout(() => {
      messageList.value!.scrollTop = messageList.value!.scrollHeight
    }, 100)
  }
}

watch(messages, scrollToBottom, {deep: true})

const handleRestart = async () => {
  if (window.confirm('确定要开始新对话吗？当前对话将被清空。')) {
    await restartChat()
  }
}

onMounted(() => {
  scrollToBottom()
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f5f7fa;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 60px;
  background: white;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h2 {
  margin: 0;
  font-size: 18px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.voice-selector {
  width: 120px;
}

.app-main {
  flex: 1;
  padding: 0;
  position: relative;
  overflow: hidden;
}

.message-list {
  height: 100%;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  -webkit-overflow-scrolling: touch;
}

.message-wrapper {
  display: flex;
  width: 100%;
}

.message-wrapper.user-message {
  justify-content: flex-end;
}

.message-wrapper.ai-message {
  justify-content: flex-start;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 70%;
  min-width: 0; /* 防止 flex 项目溢出 */
}

.message-avatar {
  flex: 0 0 40px; /* 固定头像大小，不允许缩放 */
}

.user-message .message {
  flex-direction: row-reverse;
}

.message-content {
  background: white;
  padding: 12px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  /* 修改以下属性 */
  min-width: 150px;
  width: 100%; /* 让内容区域占满可用空间 */
  overflow-wrap: break-word; /* 确保长文本正确换行 */
}

.user-message .message-content {
  background: #e6f3ff;
}

.message-audio {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.message-text {
  margin: 8px 0;
  word-break: break-word;
  white-space: pre-wrap;
  font-size: 15px;
  line-height: 1.4;
  transition: all 0.3s ease;
  overflow: hidden;
}

.message-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}

.user-message .message-actions {
  justify-content: flex-start;
}

.message-status {
  font-size: 12px;
  color: #909399;
  text-align: right;
  margin-top: 4px;
}

.user-message .message-status {
  text-align: left;
}

.play-button {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.app-footer {
  padding: 16px;
  background: white;
  box-shadow: 0 -1px 4px rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 10;
  height: auto;
}

.voice-input {
  display: flex;
  justify-content: center;
}

:deep(.el-main) {
  --el-main-padding: 0;
}

:deep(.el-header) {
  --el-header-padding: 0;
  --el-header-height: auto;
}

:deep(.el-footer) {
  --el-footer-padding: 0;
  --el-footer-height: auto;
}

.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s ease-in;
}

.slide-fade-enter-from {
  opacity: 0;
  transform: translateY(-10px);
  max-height: 0;
}

.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
  max-height: 0;
}

.slide-fade-enter-to,
.slide-fade-leave-from {
  opacity: 1;
  transform: translateY(0);
  max-height: 1000px; /* 足够大的高度以适应内容 */
}
</style>