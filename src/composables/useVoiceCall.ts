import {ref} from 'vue'

interface VoiceCallOptions {
    onAiSpeakStart: () => void
    onAiSpeakEnd: () => void
    onTranscript: (text: string, isUser: boolean) => void
}

interface CallConfig {
    voiceType: string
}

export function useVoiceCall(options: VoiceCallOptions) {
    const ws = ref<WebSocket | null>(null)
    const connectionStatus = ref<'disconnected' | 'connecting' | 'connected'>('disconnected')
    const mediaStream = ref<MediaStream | null>(null)
    const audioContext = ref<AudioContext | null>(null)

    async function initAudioContext() {
        audioContext.value = new AudioContext()

        // 获取麦克风权限
        try {
            mediaStream.value = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                }
            })

            // 创建音频处理节点
            const source = audioContext.value.createMediaStreamSource(mediaStream.value)
            const processor = audioContext.value.createScriptProcessor(1024, 1, 1)

            // 处理音频数据
            processor.onaudioprocess = (e) => {
                if (connectionStatus.value === 'connected') {
                    const audioData = e.inputBuffer.getChannelData(0)
                    sendAudioData(audioData)
                }
            }

            source.connect(processor)
            processor.connect(audioContext.value.destination)

        } catch (error) {
            console.error('Failed to initialize audio:', error)
            throw error
        }
    }

    function setupWebSocket() {
        const wsUrl = `${import.meta.env.VITE_WS_URL}/voice-call`
        ws.value = new WebSocket(wsUrl)

        ws.value.onopen = () => {
            connectionStatus.value = 'connected'
            console.log('WebSocket connected')
        }

        ws.value.onmessage = (event) => {
            const message = JSON.parse(event.data)
            handleServerMessage(message)
        }

        ws.value.onerror = (error) => {
            console.error('WebSocket error:', error)
            connectionStatus.value = 'disconnected'
        }

        ws.value.onclose = () => {
            connectionStatus.value = 'disconnected'
            console.log('WebSocket closed')
        }
    }

    function handleServerMessage(message: any) {
        switch (message.type) {
            case 'ai_speak_start':
                options.onAiSpeakStart()
                break
            case 'ai_speak_end':
                options.onAiSpeakEnd()
                break
            case 'transcript':
                options.onTranscript(message.text, message.isUser)
                break
            case 'audio':
                playAiResponse(message.audio)
                break
        }
    }

    async function playAiResponse(audioData: ArrayBuffer) {
        if (!audioContext.value) return

        try {
            const audioBuffer = await audioContext.value.decodeAudioData(audioData)
            const source = audioContext.value.createBufferSource()
            source.buffer = audioBuffer
            source.connect(audioContext.value.destination)
            source.start()
        } catch (error) {
            console.error('Failed to play AI response:', error)
        }
    }

    function sendAudioData(audioData: Float32Array) {
        if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return

        // 将音频数据转换为适合传输的格式
        const buffer = new ArrayBuffer(audioData.length * 4)
        const view = new DataView(buffer)
        for (let i = 0; i < audioData.length; i++) {
            view.setFloat32(i * 4, audioData[i])
        }

        ws.value.send(buffer)
    }

    async function startCall(config: CallConfig) {
        connectionStatus.value = 'connecting'

        try {
            await initAudioContext()
            setupWebSocket()

            // 发送初始配置
            if (ws.value) {
                ws.value.onopen = () => {
                    ws.value?.send(JSON.stringify({
                        type: 'config',
                        voiceType: config.voiceType
                    }))
                    connectionStatus.value = 'connected'
                }
            }
        } catch (error) {
            connectionStatus.value = 'disconnected'
            throw error
        }
    }

    function endCall() {
        if (ws.value) {
            ws.value.close()
            ws.value = null
        }

        if (mediaStream.value) {
            mediaStream.value.getTracks().forEach(track => track.stop())
            mediaStream.value = null
        }

        if (audioContext.value) {
            audioContext.value.close()
            audioContext.value = null
        }

        connectionStatus.value = 'disconnected'
    }

    function toggleMute() {
        if (mediaStream.value) {
            const audioTrack = mediaStream.value.getAudioTracks()[0]
            audioTrack.enabled = !audioTrack.enabled
        }
    }

    function togglePause() {
        if (ws.value && connectionStatus.value === 'connected') {
            ws.value.send(JSON.stringify({
                type: 'pause_toggle'
            }))
        }
    }

    return {
        startCall,
        endCall,
        toggleMute,
        togglePause,
        connectionStatus
    }
}