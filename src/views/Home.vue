<script setup lang="ts">
const navLinks = [
  {
    path: '/chat/voice',
    title: '☎️',
    description: '像与好友打电话一样与 Omni 聊天'
  },
  {
    path: '/',
    title: '💬',
    description: '仍在施工...'
  },
  {
    path: '/',
    title: '📹',
    description: '仍在施工...'
  }
]
</script>

<template>
  <main class="home">
    <h1>Qwen Omni Demo</h1>
    <div class="nav-grid">
      <RouterLink
          v-for="link in navLinks"
          :key="link.path"
          :to="link.path"
          class="nav-card"
      >
        <h2>{{ link.title }}</h2>
        <p>{{ link.description }}</p>
      </RouterLink>
    </div>
  </main>
</template>

<style scoped>
.home {
  padding: 2rem;
  text-align: center;
}

h1 {
  margin-bottom: 3rem;
  color: #2c3e50;
}

.nav-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.nav-card {
  display: block;
  padding: 1.5rem;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  text-decoration: none;
  transition: transform 0.2s, box-shadow 0.2s;
}

.nav-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.nav-card h2 {
  color: #2c3e50;
  margin: 0 0 0.5rem;
  font-size: 1.5rem;
}

.nav-card p {
  color: #666;
  margin: 0;
  font-size: 1rem;
}
</style>