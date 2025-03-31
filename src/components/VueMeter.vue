<template>
  <canvas ref="canvas" :width="width" :height="height"></canvas>
</template>

<script setup lang="ts">
import {onMounted, onUnmounted, ref, watch} from 'vue'

const props = withDefaults(defineProps<{
  audioLevel: number
  width: number
  height: number
}>(), {
  audioLevel: 0,
  width: 200,
  height: 50
})

const canvas = ref<HTMLCanvasElement | null>(null)
let animationFrame: number | null = null

function draw() {
  if (!canvas.value) return

  const ctx = canvas.value.getContext('2d')
  if (!ctx) return

  // 清除画布
  ctx.clearRect(0, 0, props.width, props.height)

  // 归一化音量级别
  const normalizedLevel = Math.max(0, Math.min(1, props.audioLevel || 0))

  // 绘制音量条
  const barWidth = 4
  const barGap = 2
  const barCount = Math.floor(props.width / (barWidth + barGap))
  const maxHeight = props.height - 4

  for (let i = 0; i < barCount; i++) {
    // 根据音量级别计算每个条的高度
    const height = Math.min(normalizedLevel * maxHeight, maxHeight)
    const randomHeight = height * (0.8 + Math.random() * 0.3)

    const x = i * (barWidth + barGap)
    const y = Math.max(0, props.height - randomHeight)

    try {
      const gradient = ctx.createLinearGradient(0, y, 0, props.height)
      gradient.addColorStop(0, '#409EFF')
      gradient.addColorStop(1, '#79bbff')
      ctx.fillStyle = gradient
      ctx.fillRect(x, y, barWidth, randomHeight)
    } catch (error) {
      // 渐变失败回退到单色
      ctx.fillStyle = '#409EFF'
      ctx.fillRect(x, y, barWidth, randomHeight)
    }
  }

  animationFrame = requestAnimationFrame(draw)
}

watch(() => props.audioLevel, () => {
  if (animationFrame === null) {
    draw()
  }
}, {immediate: true})

onMounted(() => {
  draw()
})

onUnmounted(() => {
  if (animationFrame !== null) {
    cancelAnimationFrame(animationFrame)
  }
})
</script>