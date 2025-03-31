import {ref} from 'vue'

export function useAudioVisualization() {
    const audioLevel = ref(0)
    let audioContext: AudioContext | null = null
    let analyzer: AnalyserNode | null = null
    let mediaStream: MediaStream | null = null
    let animationFrame: number | null = null

    const startVisualization = async () => {
        try {
            mediaStream = await navigator.mediaDevices.getUserMedia({audio: true})
            audioContext = new AudioContext()
            analyzer = audioContext.createAnalyser()

            const source = audioContext.createMediaStreamSource(mediaStream)
            source.connect(analyzer)

            analyzer.fftSize = 256
            const bufferLength = analyzer.frequencyBinCount
            const dataArray = new Uint8Array(bufferLength)

            const updateLevel = () => {
                if (!analyzer) return

                analyzer.getByteFrequencyData(dataArray)
                const average = dataArray.reduce((acc, val) => acc + val, 0) / bufferLength
                audioLevel.value = average / 255 // 标准化到 0-1

                animationFrame = requestAnimationFrame(updateLevel)
            }

            updateLevel()
        } catch (error) {
            console.error('Audio visualization error:', error)
            throw error
        }
    }

    const stopVisualization = () => {
        if (animationFrame) {
            cancelAnimationFrame(animationFrame)
        }
        if (mediaStream) {
            mediaStream.getTracks().forEach(track => track.stop())
        }
        if (audioContext) {
            audioContext.close()
        }
        audioLevel.value = 0
        analyzer = null
        mediaStream = null
        audioContext = null
    }

    return {
        audioLevel,
        startVisualization,
        stopVisualization
    }
}