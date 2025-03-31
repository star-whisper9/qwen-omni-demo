<script setup lang="ts">
import {computed, onUnmounted, ref} from 'vue'
import {ElMessage} from 'element-plus'
import {ArrowLeft, Close, Microphone, Mute, PhoneFilled, VideoPause, VideoPlay} from "@element-plus/icons-vue";
import VueMeter from '@/components/VueMeter.vue'
import {useVoiceCall} from '@/composables/useVoiceCall'
import {useAudioVisualization} from '@/composables/useAudioVisualization'

const aiAvatar = '/qwen.png'

const voiceType = ref('Chelsie')
const isInCall = ref(false)
const isMuted = ref(false)
const isPaused = ref(false)
const showCaptions = ref(true)
const isMicTesting = ref(false)
const isMicrophoneReady = ref(false)
const callDuration = ref(0)
const userCaption = ref('')
const aiCaption = ref('')
const aiSpeaking = ref(false)

const {
  startCall: initializeCall,
  endCall: terminateCall,
  toggleMute: toggleMicrophone,
  togglePause: toggleCallPause,
  connectionStatus: callConnectionStatus,
} = useVoiceCall({
  onAiSpeakStart: () => {
    aiSpeaking.value = true
  },
  onAiSpeakEnd: () => {
    aiSpeaking.value = false
  },
  onTranscript: (text: string, isUser: boolean) => {
    if (isUser) {
      userCaption.value = text
    } else {
      aiCaption.value = text
    }
  }
})

const {
  startVisualization,
  stopVisualization,
  audioLevel,
} = useAudioVisualization()

const connectionStatus = computed(() => {
  return {
    type: callConnectionStatus.value === 'connected' ? 'success' :
        callConnectionStatus.value === 'connecting' ? 'warning' : 'danger',
    text: callConnectionStatus.value === 'connected' ? '已连接' :
        callConnectionStatus.value === 'connecting' ? '连接中...' : '未连接'
  }
})

async function testMicrophone() {
  if (isMicTesting.value) {
    await stopVisualization()
    isMicTesting.value = false
    return
  }

  try {
    await startVisualization()
    isMicTesting.value = true
    isMicrophoneReady.value = true
  } catch (error) {
    ElMessage.error('无法访问麦克风')
    console.error('Microphone access error:', error)
  }
}

async function startCall() {
  try {
    isInCall.value = true
    await initializeCall({
      voiceType: voiceType.value
    })
    startCallTimer()
  } catch (error) {
    ElMessage.error('开始通话失败')
    isInCall.value = false
  }
}

async function endCall() {
  try {
    await terminateCall()
    await stopVisualization()
    isInCall.value = false
    stopCallTimer()
  } catch (error) {
    ElMessage.error('结束通话失败')
  }
}

function toggleMute() {
  isMuted.value = !isMuted.value
  toggleMicrophone()
}

function togglePause() {
  isPaused.value = !isPaused.value
  toggleCallPause()
}

let timer: number | null = null

function startCallTimer() {
  callDuration.value = 0
  timer = window.setInterval(() => {
    callDuration.value++
  }, 1000)
}

function stopCallTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  callDuration.value = 0
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

onUnmounted(() => {
  if (isInCall.value) {
    endCall()
  }
  stopVisualization()
  stopCallTimer()
})
</script>

<template>
  <el-container class="call-container">
    <el-header class="call-header">
      <div class="status-bar">
        <router-link to="/">
          <el-button type="info" :icon="ArrowLeft" style="margin-right: 20px">返回</el-button>
        </router-link>
        <el-tag :type="connectionStatus.type">
          {{ connectionStatus.text }}
        </el-tag>
        <el-tag v-if="isInCall" type="success">
          通话时长: {{ formatDuration(callDuration) }}
        </el-tag>
      </div>

      <div class="voice-settings">
        <el-select v-model="voiceType" placeholder="AI 声音" :disabled="isInCall" style="width: 240px">
          <el-option label="Chelsie (女声)" value="Chelsie"/>
          <el-option label="Ethan (男声)" value="Ethan"/>
        </el-select>
      </div>
    </el-header>

    <el-main class="call-main">
      <div class="call-interface" :class="{ 'in-call': isInCall }">
        <template v-if="!isInCall">
          <div class="pre-call">
            <el-avatar :size="120" :src="aiAvatar"/>
            <h2>Qwen AI Assistant</h2>
            <div class="audio-level-indicator" v-if="isMicTesting">
              <!-- 音量可视化组件 -->
              <VueMeter
                  :audioLevel="audioLevel"
                  :width="200"
                  :height="40"
              />
            </div>
            <div class="pre-call-actions">
              <el-button
                  @click="testMicrophone"
                  :icon="isMicTesting ? Close : Microphone"
                  :type="isMicTesting ? 'danger' : 'info'">
                {{ isMicTesting ? '停止测试' : '测试麦克风' }}
              </el-button>
              <el-button
                  type="primary"
                  @click="startCall"
                  :disabled="!isMicrophoneReady"
                  :icon="VideoPlay">
                开始通话
              </el-button>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="active-call">
            <el-avatar :size="120" :src="aiAvatar" :class="{ speaking: aiSpeaking }"/>

            <!-- 实时音量显示 -->
            <div class="audio-visualization">
              <VueMeter
                  :audioLevel="audioLevel"
                  :width="300"
                  :height="60"
              />
            </div>

            <!-- 通话控制按钮 -->
            <div class="call-controls">
              <el-button
                  :type="isMuted ? 'danger' : 'info'"
                  circle
                  @click="toggleMute"
                  :icon="isMuted ? Mute : Microphone"
              />
              <el-button
                  type="danger"
                  @click="endCall"
                  :icon="PhoneFilled"
              >
                挂断
              </el-button>
              <el-button
                  :type="isPaused ? 'warning' : 'info'"
                  circle
                  @click="togglePause"
                  :icon="isPaused ? VideoPlay : VideoPause"
              />
            </div>
          </div>
        </template>
      </div>
    </el-main>

    <!-- 可选的字幕显示区域 -->
    <el-footer v-if="isInCall" class="caption-area">
      <div class="captions" v-if="showCaptions">
        <p class="user-caption">{{ userCaption }}</p>
        <p class="ai-caption">{{ aiCaption }}</p>
      </div>
      <el-switch
          v-model="showCaptions"
          active-text="显示字幕"
      />
    </el-footer>
  </el-container>
</template>

<style scoped>
.call-container {
  height: 100vh;
  background: #f5f7fa;
}

.call-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: white;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.call-main {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
}

.call-interface {
  width: 100%;
  max-width: 800px;
  aspect-ratio: 16/9;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 24px 0 rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: center;
  align-items: center;
}

.pre-call,
.active-call {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.call-controls {
  display: flex;
  gap: 12px;
}

.speaking {
  animation: pulse 1.2s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(64, 158, 255, 0.4);
  }
  70% {
    box-shadow: 0 0 0 20px rgba(64, 158, 255, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(64, 158, 255, 0);
  }
}

.caption-area {
  background: white;
  padding: 20px;
  border-top: 1px solid #eee;
}

.captions {
  margin-bottom: 10px;
  text-align: center;
}

.user-caption {
  color: #606266;
}

.ai-caption {
  color: #409EFF;
  font-weight: 500;
}
</style>