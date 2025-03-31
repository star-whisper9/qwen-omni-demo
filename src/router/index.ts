import {createRouter, createWebHistory} from 'vue-router'
import Home from "@/views/Home.vue";
import VoiceChat from "@/views/VoiceChat.vue";

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: "/",
            component: Home,
        },
        {
            path: "/chat/voice",
            component: VoiceChat,
        }
    ],
})

export default router
