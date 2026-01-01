<!--
  JARVIS Main Dashboard - 3-column responsive layout
-->
<script lang="ts">
    import { onMount } from "svelte";
    import HudCore from "$lib/components/HudCore.svelte";
    import LiveGraph from "$lib/components/LiveGraph.svelte";
    import LogTerminal from "$lib/components/LogTerminal.svelte";
    import MemoryIndicator from "$lib/components/MemoryIndicator.svelte";
    import ChatInterface from "$lib/components/ChatInterface.svelte";
    import ModelSettings from "$lib/components/ModelSettings.svelte";
    import {
        initSensorListeners,
        isConnected,
        weather,
    } from "$lib/stores/sensors";
    import {
        loadUserProfile,
        loadPreferences,
        userProfile,
    } from "$lib/stores/memory";
    import "../app.css";

    let currentTime = "";
    let currentDate = "";

    function updateClock() {
        const now = new Date();
        currentTime = now.toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false,
        });
        currentDate = now.toLocaleDateString("en-US", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
        });
    }

    onMount(async () => {
        // Initialize clock
        updateClock();
        setInterval(updateClock, 1000);

        // Initialize sensor listeners
        await initSensorListeners();

        // Load user data
        await loadUserProfile();
        await loadPreferences();
    });
</script>

<div class="jarvis-dashboard">
    <!-- Left Panel: System Status -->
    <aside class="panel left-panel">
        <div class="panel-header">SYSTEM STATUS</div>
        <div class="panel-content">
            <div class="status-row">
                <span class="status-label">CONNECTION</span>
                <span class="status-value">
                    <span class="status-dot" class:active={$isConnected}></span>
                    {$isConnected ? "ONLINE" : "OFFLINE"}
                </span>
            </div>

            <LiveGraph title="CPU Load" type="cpu" height={50} />
            <LiveGraph title="Memory" type="memory" height={50} />

            <div class="weather-section panel">
                <div class="panel-header">WEATHER</div>
                <div class="panel-content">
                    {#if $weather}
                        <div class="weather-temp">
                            {$weather.temperature}°{$weather.unit}
                        </div>
                        <div class="weather-cond">{$weather.conditions}</div>
                    {:else}
                        <div class="weather-loading">Loading...</div>
                    {/if}
                </div>
            </div>
        </div>
    </aside>

    <!-- Center Panel: Main Interface -->
    <main class="center-panel">
        <header class="top-bar">
            <div class="time-display">
                <div class="time">{currentTime}</div>
                <div class="date">{currentDate}</div>
            </div>
            <div class="user-greeting">
                {#if $userProfile.name}
                    Welcome, {$userProfile.name}
                {:else}
                    JARVIS READY
                {/if}
            </div>
        </header>

        <HudCore />

        <div class="chat-section">
            <ChatInterface />
        </div>

        <LogTerminal />
    </main>

    <!-- Right Panel: Memory & Tools -->
    <aside class="panel right-panel">
        <div class="panel-header">MEMORY SYSTEM</div>
        <div class="panel-content">
            <MemoryIndicator />

            <div class="memory-browser panel">
                <div class="panel-header">RECENT MEMORIES</div>
                <div class="panel-content memory-list">
                    <p class="empty-state">
                        Memories will appear here as JARVIS learns about you.
                    </p>
                </div>
            </div>

            <div class="tools-icons">
                <div class="tool-icon-compact weather" title="Weather">🌤️</div>
                <div class="tool-icon-compact transit" title="Transit">🚇</div>
                <div class="tool-icon-compact flights" title="Flights">✈️</div>
                <div class="tool-icon-compact memory" title="Memory">🧠</div>
            </div>

            <ModelSettings />
        </div>
    </aside>
</div>

<style>
    .jarvis-dashboard {
        display: grid;
        grid-template-columns: 280px 1fr 280px;
        gap: var(--space-md);
        height: 100vh;
        padding: var(--space-md);
        background: var(--bg-dark);
    }

    @media (max-width: 1200px) {
        .jarvis-dashboard {
            grid-template-columns: 240px 1fr 240px;
        }
    }

    @media (max-width: 900px) {
        .jarvis-dashboard {
            grid-template-columns: 1fr;
            grid-template-rows: auto 1fr auto;
            overflow-y: auto;
        }

        .left-panel,
        .right-panel {
            display: none; /* Hide sidebars on mobile */
        }
    }

    .left-panel,
    .right-panel {
        display: flex;
        flex-direction: column;
        overflow-y: auto;
    }

    .left-panel .panel-content,
    .right-panel .panel-content {
        display: flex;
        flex-direction: column;
        gap: var(--space-md);
    }

    .center-panel {
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }

    .top-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: var(--space-md);
        background: var(--bg-panel);
        border: var(--border-subtle);
        border-radius: 4px;
        margin-bottom: var(--space-md);
    }

    .time-display {
        text-align: left;
    }

    .time {
        font-family: var(--font-display);
        font-size: 1.5rem;
        color: var(--primary-blue);
        text-shadow: var(--glow-sm);
        letter-spacing: 0.1em;
    }

    .date {
        font-size: 0.75rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    .user-greeting {
        font-family: var(--font-display);
        font-size: 0.8rem;
        color: var(--text-secondary);
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    .chat-section {
        flex: 1;
        min-height: 0;
        margin-bottom: var(--space-md);
    }

    .status-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: var(--space-sm);
        background: var(--bg-darker);
        border-radius: 4px;
    }

    .status-label {
        font-size: 0.7rem;
        color: var(--text-muted);
        letter-spacing: 0.1em;
    }

    .status-value {
        display: flex;
        align-items: center;
        gap: var(--space-xs);
        font-size: 0.75rem;
        color: var(--text-secondary);
    }

    .weather-section {
        padding: 0;
    }

    .weather-temp {
        font-family: var(--font-display);
        font-size: 1.5rem;
        color: var(--primary-blue);
    }

    .weather-cond {
        font-size: 0.8rem;
        color: var(--text-muted);
    }

    .weather-loading {
        font-size: 0.8rem;
        color: var(--text-muted);
        font-style: italic;
    }

    .memory-list {
        min-height: 100px;
    }

    .empty-state {
        font-size: 0.75rem;
        color: var(--text-muted);
        font-style: italic;
        text-align: center;
        padding: var(--space-md);
    }

    .tool-item {
        display: flex;
        align-items: center;
        gap: var(--space-sm);
        padding: var(--space-xs) 0;
        border-bottom: var(--border-subtle);
    }

    .tool-item:last-child {
        border-bottom: none;
    }

    .tool-icon {
        font-size: 1.2rem;
    }

    .tools-icons {
        display: flex;
        gap: var(--space-sm);
        justify-content: center;
        padding: var(--space-sm) 0;
    }

    .tool-icon-compact {
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        font-size: 1.2rem;
        cursor: pointer;
        transition: all 0.2s ease;
        opacity: 0.7;
    }

    .tool-icon-compact:hover {
        opacity: 1;
        transform: scale(1.1);
    }

    .tool-icon-compact.weather {
        background: linear-gradient(135deg, #f39c12, #e67e22);
        box-shadow: 0 0 10px rgba(243, 156, 18, 0.3);
    }

    .tool-icon-compact.transit {
        background: linear-gradient(135deg, #3498db, #2980b9);
        box-shadow: 0 0 10px rgba(52, 152, 219, 0.3);
    }

    .tool-icon-compact.flights {
        background: linear-gradient(135deg, #9b59b6, #8e44ad);
        box-shadow: 0 0 10px rgba(155, 89, 182, 0.3);
    }

    .tool-icon-compact.memory {
        background: linear-gradient(135deg, #00ff88, #00cc6a);
        box-shadow: 0 0 10px rgba(0, 255, 136, 0.3);
    }
</style>
