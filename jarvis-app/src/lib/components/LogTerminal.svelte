<!--
  LogTerminal.svelte - Displays AI thought process
  Shows real-time logs of RAG retrieval and inference steps
-->
<script lang="ts">
    import { thoughtLogs } from '$lib/stores/chat';
    import { onMount, afterUpdate } from 'svelte';

    let terminalEl: HTMLDivElement;
    let autoScroll = true;

    function formatTime(timestamp: number): string {
        const date = new Date(timestamp * 1000);
        return date.toLocaleTimeString('en-US', { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });
    }

    function handleScroll() {
        if (!terminalEl) return;
        const { scrollTop, scrollHeight, clientHeight } = terminalEl;
        autoScroll = scrollTop + clientHeight >= scrollHeight - 10;
    }

    afterUpdate(() => {
        if (autoScroll && terminalEl) {
            terminalEl.scrollTop = terminalEl.scrollHeight;
        }
    });

    // Demo logs for initial state
    const demoLogs = [
        { step: 'INIT', detail: 'JARVIS Core v2.0 initialized', timestamp: Date.now() / 1000 },
        { step: 'SENSOR', detail: 'System monitoring active', timestamp: Date.now() / 1000 },
        { step: 'MEMORY', detail: 'SQLite store connected', timestamp: Date.now() / 1000 },
    ];
</script>

<div class="log-terminal panel">
    <div class="panel-header">
        <span>SYSTEM LOG</span>
        <span class="blink-cursor">_</span>
    </div>
    <div class="terminal-content" bind:this={terminalEl} on:scroll={handleScroll}>
        {#each demoLogs as log}
            <div class="log-entry demo">
                <span class="timestamp">[{formatTime(log.timestamp)}]</span>
                <span class="step">{log.step}:</span>
                <span class="detail">{log.detail}</span>
            </div>
        {/each}
        
        {#each $thoughtLogs as log}
            <div class="log-entry animate-fade-in">
                <span class="timestamp">[{formatTime(log.timestamp)}]</span>
                <span class="step">{log.step}:</span>
                <span class="detail">{log.detail}</span>
            </div>
        {/each}

        {#if $thoughtLogs.length === 0}
            <div class="log-entry waiting">
                <span class="detail">Awaiting commands...</span>
            </div>
        {/if}
    </div>
</div>

<style>
    .log-terminal {
        display: flex;
        flex-direction: column;
        max-height: 200px;
    }

    .panel-header {
        display: flex;
        justify-content: space-between;
        padding: var(--space-sm) var(--space-md);
        border-bottom: var(--border-subtle);
        font-family: var(--font-display);
        font-size: 0.7rem;
        letter-spacing: 0.15em;
        color: var(--primary-blue);
    }

    .blink-cursor {
        animation: blink 1s step-end infinite;
    }

    .terminal-content {
        flex: 1;
        overflow-y: auto;
        padding: var(--space-sm);
        font-family: var(--font-mono);
        font-size: 0.75rem;
        line-height: 1.6;
    }

    .log-entry {
        margin-bottom: 2px;
    }

    .log-entry.demo {
        opacity: 0.5;
    }

    .log-entry.waiting {
        color: var(--text-muted);
        font-style: italic;
    }

    .timestamp {
        color: var(--text-muted);
        margin-right: var(--space-xs);
    }

    .step {
        color: var(--primary-blue);
        margin-right: var(--space-xs);
        font-weight: 500;
    }

    .detail {
        color: var(--text-secondary);
    }

    @keyframes blink {
        50% { opacity: 0; }
    }
</style>
