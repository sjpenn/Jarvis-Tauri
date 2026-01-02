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
    import TransitTicket from "$lib/components/TransitTicket.svelte";
    import { listen } from "@tauri-apps/api/event";
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
    import { llmStatus } from "$lib/stores/llm";
    import "../app.css";
    let currentDate = "";
    let showServicesPanel = false;
    let currentTransitRoute = null; // New state for transit data

    function updateClock() {
        // ... (existing clock logic)
    }

    onMount(async () => {
        // Initialize clock
        updateClock();
        const clockInterval = setInterval(updateClock, 1000);

        // Initialize sensors and memory
        await initSensorListeners();
        await loadUserProfile();
        await loadPreferences();

        // Listen for transit events

        // Listen for transit events
        const unlisten = await listen("chat:transit", (event) => {
            console.log("Received transit data:", event.payload);
            currentTransitRoute = event.payload;
            // Auto-open chat if needed, or just show it
        });

        return () => {
            unlisten();
        };
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

            <LogTerminal />
        </div>
    </aside>

    <!-- Center Panel: Main Interface -->
    <main class="center-panel">
        <header class="top-bar">
            <!-- ... -->
        </header>

        <HudCore />

        <div class="chat-section">
            <ChatInterface />
            {#if currentTransitRoute}
                <div class="transit-overlay">
                    <button
                        class="close-ticket"
                        on:click={() => (currentTransitRoute = null)}>✕</button
                    >
                    <TransitTicket route={currentTransitRoute} />
                </div>
            {/if}
        </div>
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

            <button
                class="status-link"
                on:click={() => (showServicesPanel = true)}
            >
                VIEW SERVICES STATUS →
            </button>

            <ModelSettings />
        </div>
    </aside>
</div>

<!-- Slide-out Services Panel -->
{#if showServicesPanel}
    <div
        class="services-backdrop"
        on:click={() => (showServicesPanel = false)}
    ></div>
    <div class="services-panel">
        <div class="services-header">
            <span>SERVICES STATUS</span>
            <button
                class="close-btn"
                on:click={() => (showServicesPanel = false)}>✕</button
            >
        </div>
        <div class="services-list">
            <div class="service-item">
                <span class="service-icon">🌤️</span>
                <div class="service-info">
                    <span class="service-name">Weather</span>
                    <span class="service-provider">Open-Meteo</span>
                </div>
                <span class="service-status online">ONLINE</span>
            </div>
            <div class="service-item">
                <span class="service-icon">🚇</span>
                <div class="service-info">
                    <span class="service-name">Transit</span>
                    <span class="service-provider">WMATA API</span>
                </div>
                <span class="service-status online">ONLINE</span>
            </div>
            <div class="service-item">
                <span class="service-icon">✈️</span>
                <div class="service-info">
                    <span class="service-name">Flights</span>
                    <span class="service-provider">OpenSky Network</span>
                </div>
                <span class="service-status online">ONLINE</span>
            </div>
            <div class="service-item">
                <span class="service-icon">🧠</span>
                <div class="service-info">
                    <span class="service-name">Memory</span>
                    <span class="service-provider">SQLite Local</span>
                </div>
                <span class="service-status online">ACTIVE</span>
            </div>
            <div class="service-item">
                <span class="service-icon">🤖</span>
                <div class="service-info">
                    <span class="service-name">LLM</span>
                    <span class="service-provider">Phi-3 Mini</span>
                </div>
                <!-- PENDING, LOADING, READY, ERROR -->
                <span
                    class="service-status"
                    class:pending={$llmStatus === "PENDING"}
                    class:online={$llmStatus === "READY" ||
                        $llmStatus === "LOADING"}
                    class:offline={$llmStatus === "ERROR"}
                >
                    {$llmStatus === "LOADING" ? "LOADING..." : $llmStatus}
                </span>
            </div>
        </div>
    </div>
{/if}

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
            display: flex;
            flex-direction: column;
            height: auto;
            min-height: 100vh;
            overflow-y: auto;
        }

        .center-panel {
            order: 1;
            height: 80vh; /* Give chat priority on mobile */
            min-height: 500px;
        }

        .right-panel {
            order: 2;
            width: 100%;
            height: auto;
            border-top: var(--border-subtle);
        }

        .left-panel {
            order: 3;
            width: 100%;
            height: auto;
            border-top: var(--border-subtle);
        }

        .panel-content {
            gap: var(--space-sm);
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

    .status-link {
        width: 100%;
        padding: var(--space-md);
        background: transparent;
        border: 1px solid var(--primary-blue);
        border-radius: 4px;
        color: var(--primary-blue);
        font-family: var(--font-display);
        font-size: 0.7rem;
        letter-spacing: 0.1em;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .status-link:hover {
        background: rgba(0, 243, 255, 0.1);
        box-shadow: var(--glow-sm);
    }

    .services-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        z-index: 100;
        animation: fade-in 0.2s ease;
    }

    .services-panel {
        position: fixed;
        top: 0;
        right: 0;
        width: 350px;
        height: 100%;
        background: rgba(10, 25, 35, 0.95);
        backdrop-filter: blur(20px);
        border-left: 1px solid var(--primary-blue);
        z-index: 101;
        animation: slide-in 0.3s ease;
        display: flex;
        flex-direction: column;
    }

    .services-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: var(--space-lg);
        border-bottom: var(--border-subtle);
        font-family: var(--font-display);
        font-size: 0.9rem;
        letter-spacing: 0.15em;
        color: var(--primary-blue);
    }

    .close-btn {
        background: none;
        border: none;
        color: var(--text-muted);
        font-size: 1.2rem;
        cursor: pointer;
        padding: 4px;
    }

    .close-btn:hover {
        color: var(--primary-blue);
    }

    .services-list {
        flex: 1;
        overflow-y: auto;
        padding: var(--space-md);
    }

    .service-item {
        display: flex;
        align-items: center;
        gap: var(--space-md);
        padding: var(--space-md);
        border-radius: 8px;
        background: rgba(0, 100, 130, 0.1);
        margin-bottom: var(--space-sm);
        transition: all 0.2s ease;
    }

    .service-item:hover {
        background: rgba(0, 100, 130, 0.2);
    }

    .service-icon {
        font-size: 1.5rem;
    }

    .service-info {
        flex: 1;
        display: flex;
        flex-direction: column;
    }

    .service-name {
        font-family: var(--font-display);
        font-size: 0.85rem;
        color: var(--text-primary);
    }

    .service-provider {
        font-size: 0.7rem;
        color: var(--text-muted);
    }

    .service-status {
        font-family: var(--font-mono);
        font-size: 0.65rem;
        padding: 4px 8px;
        border-radius: 4px;
        letter-spacing: 0.1em;
    }

    .service-status.online {
        background: rgba(0, 255, 136, 0.15);
        color: var(--success-green);
        border: 1px solid var(--success-green);
    }

    .service-status.pending {
        background: rgba(255, 213, 0, 0.15);
        color: var(--warning-yellow);
        border: 1px solid var(--warning-yellow);
    }

    .service-status.offline {
        background: rgba(255, 42, 42, 0.15);
        color: var(--alert-red);
        border: 1px solid var(--alert-red);
    }

    @keyframes fade-in {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }

    @keyframes slide-in {
        from {
            transform: translateX(100%);
        }
        to {
            transform: translateX(0);
        }
    }
</style>
