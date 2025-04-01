import {onMounted, ref, watch} from 'vue'
import {ElMessage} from 'element-plus'

interface VoiceType {
    id: string
    name: string
}

interface Message {
    id: string
    content: string
    isUser: boolean
    timestamp: number
    audioData?: string
    status: 'sending' | 'sent' | 'error'
    showText: boolean
}

interface ChatProps {
    onMessageStatusChange?: (messageId: string, status: Message['status']) => void
}

export function useVoiceChat(props: ChatProps) {
    const messages = ref<Message[]>([])
    const isRecording = ref(false)
    const mediaRecorder = ref<MediaRecorder | null>(null)
    const clientId = ref<string>(crypto.randomUUID())
    const currentVoice = ref<string>('Chelsie')

    const availableVoices = ref<VoiceType[]>([
        {id: 'Chelsie', name: 'Chelsie'},
        {id: 'Ethan', name: 'Ethan'}
    ])

    let recordedChunks: Blob[] = []

    async function initChat() {
        try {
            console.info('[VoiceChat] Initializing API request')
            const response = await fetch('/api/config', {  // 使用相对路径
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    clientId: clientId.value,
                    voiceType: currentVoice.value
                })
            })
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }
            const data = await response.json()
            console.info('[VoiceChat] Session initialized:', data)
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error)
            console.error('[VoiceChat] Init error:', errorMessage)
            ElMessage.error(`初始化失败: ${errorMessage}`)
        }
    }

    const loadFromStorage = () => {
        const storedMessages = localStorage.getItem('chat_messages')
        const storedClientId = localStorage.getItem('chat_client_id')

        if (storedMessages) {
            messages.value = JSON.parse(storedMessages)
        }

        if (storedClientId) {
            clientId.value = storedClientId
        } else {
            clientId.value = crypto.randomUUID()
            localStorage.setItem('chat_client_id', clientId.value)
        }
    }

    // 保存消息到本地存储
    const saveToStorage = () => {
        localStorage.setItem('chat_messages', JSON.stringify(messages.value))
    }

    // 监听消息变化
    watch(messages, () => {
        saveToStorage()
    }, {deep: true})

    const restartChat = async () => {
        messages.value = []
        clientId.value = crypto.randomUUID()
        localStorage.setItem('chat_client_id', clientId.value)
        saveToStorage()
        await initChat()
    }

    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({audio: true})
            mediaRecorder.value = new MediaRecorder(stream, {
                // 直接录制为 WAV 格式
                mimeType: 'audio/webm'
            })

            mediaRecorder.value.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    recordedChunks.push(event.data)
                }
            }

            mediaRecorder.value.onstop = async () => {
                if (recordedChunks.length === 0) return
                await sendRecordingToServer()
                recordedChunks = []
            }

            mediaRecorder.value.start(100)
            isRecording.value = true
            console.info('[VoiceChat] Started recording')
        } catch (error) {
            console.error('[VoiceChat] Recording error:', error)
            ElMessage.error('无法访问麦克风')
        }
    }

    function stopRecording() {
        if (mediaRecorder.value && mediaRecorder.value.state === 'recording') {
            mediaRecorder.value.stop()
            mediaRecorder.value.stream.getTracks().forEach(track => track.stop())
            isRecording.value = false
            console.info('[VoiceChat] Stopped recording')
        }
    }

    async function sendRecordingToServer() {
        const messageId = crypto.randomUUID()
        try {
            const audioBlob = new Blob(recordedChunks, {type: 'audio/webm'})
            const base64Audio = await blobToBase64(audioBlob)

            messages.value.push({
                id: messageId,
                content: '正在发送语音消息...',
                isUser: true,
                timestamp: Date.now(),
                audioData: base64Audio,
                status: 'sending',
                showText: false
            })

            const response = await fetch(`${import.meta.env.VITE_BACK_HTTP_URL}/api/chat`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    audio: base64Audio,
                    audioType: 'webm',  // 告诉后端音频格式
                    clientId: clientId.value,
                    voiceType: currentVoice.value
                })
            })

            const data = await response.json()

            if (data.status === 'success') {
                const userMessage = messages.value.find(m => m.id === messageId)
                if (userMessage) {
                    userMessage.status = 'sent'
                    userMessage.content = data.userTranscript || '语音消息'
                }

                messages.value.push({
                    id: crypto.randomUUID(),
                    content: data.aiTranscript,
                    isUser: false,
                    timestamp: Date.now(),
                    audioData: data.audioResponse,
                    status: 'sent',
                    showText: false
                })

                // 收到消息自动播放一次
                await playAudio(data.audioResponse)
            } else {
                throw new Error(data.message || 'Failed to send message')
            }
        } catch (error) {
            console.error('[VoiceChat] Send error:', error)
            const message = messages.value.find(m => m.id === messageId)
            if (message) {
                message.status = 'error'
                message.content = '发送失败'
            }
            ElMessage.error('发送消息失败')
        }
    }

    function blobToBase64(blob: Blob): Promise<string> {
        return new Promise((resolve, reject) => {
            const reader = new FileReader()
            reader.onloadend = () => {
                const base64String = reader.result as string
                resolve(base64String.split(',')[1]) // 移除 data:audio/wav;base64, 前缀
            }
            reader.onerror = reject
            reader.readAsDataURL(blob)
        })
    }

    function setVoiceType(voiceType: string) {
        currentVoice.value = voiceType
        console.info('[VoiceChat] Voice type changed:', voiceType)
    }

    async function playAudio(audioData: string) {
        const audio = new Audio(`data:audio/wav;base64,${audioData}`)
        await audio.play()
    }

    function cleanup() {
        if (mediaRecorder.value) {
            mediaRecorder.value.stream.getTracks().forEach(track => track.stop())
        }
        messages.value = []
    }

    onMounted(() => {
        loadFromStorage()
        initChat()
    })

    return {
        messages,
        isRecording,
        startRecording,
        stopRecording,
        playAudio,
        cleanup,
        availableVoices,
        currentVoice,
        setVoiceType,
        restartChat
    }
}