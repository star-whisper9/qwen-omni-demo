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

    function setupWebSocket(config: CallConfig) {
        const clientId = crypto.randomUUID()
        const wsUrl = `${import.meta.env.VITE_WS_URL}/ws/${clientId}`
        ws.value = new WebSocket(wsUrl)

        // 设置配置WebSocket
        const configWs = new WebSocket(`ws://localhost:6006/ws/${clientId}/config`)
        configWs.onopen = () => {
            configWs.send(JSON.stringify({
                type: 'config',
                voiceType: config.voiceType
            }))
        }

        ws.value.onopen = () => {
            connectionStatus.value = 'connected'
            console.log('WebSocket connected')
        }

        ws.value.onmessage = async (event) => {
            if (event.data instanceof Blob) {
                // 处理音频数据
                const arrayBuffer = await event.data.arrayBuffer()
                await playAiResponse(arrayBuffer)
            } else {
                // 处理JSON消息
                const message = JSON.parse(event.data)
                handleServerMessage(message)
            }
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

    async function sendAudioData(audioData: Float32Array) {
        if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return

        // 创建WAV文件
        const wavBlob = await floatTo16BitPCM(audioData, 24000)
        ws.value.send(await wavBlob.arrayBuffer())
    }

    function floatTo16BitPCM(float32Array: Float32Array, sampleRate: number): Blob {
        const wavHeader = createWavHeader(float32Array.length, sampleRate)
        const pcmData = new Int16Array(float32Array.length)

        // 转换为16位PCM
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]))
            pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
        }

        return new Blob([wavHeader, pcmData.buffer], {type: 'audio/wav'})
    }

    function createWavHeader(dataLength: number, sampleRate: number): ArrayBuffer {
        const header = new ArrayBuffer(44)
        const view = new DataView(header)

        // WAV Header格式设置
        writeString(view, 0, 'RIFF')
        view.setUint32(4, 36 + dataLength * 2, true)
        writeString(view, 8, 'WAVE')
        writeString(view, 12, 'fmt ')
        view.setUint32(16, 16, true)
        view.setUint16(20, 1, true)
        view.setUint16(22, 1, true)
        view.setUint32(24, sampleRate, true)
        view.setUint32(28, sampleRate * 2, true)
        view.setUint16(32, 2, true)
        view.setUint16(34, 16, true)
        writeString(view, 36, 'data')
        view.setUint32(40, dataLength * 2, true)

        return header
    }

    function writeString(view: DataView, offset: number, string: string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i))
        }
    }

    async function startCall(config: CallConfig) {
        connectionStatus.value = 'connecting'

        try {
            await initAudioContext()
            setupWebSocket(config)

            // 发送初始配置
            if (ws.value) {
                ws.value.onopen = () => {
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