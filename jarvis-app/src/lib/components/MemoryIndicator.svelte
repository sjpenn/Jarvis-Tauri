<!--
  MemoryIndicator.svelte - Visual indicator for vector store access
  Glows when SQLite-VSS is being queried for context retrieval
-->
<script lang="ts">
    import { memoryAccessActive, memories, userProfile } from '$lib/stores/memory';
</script>

<div class="memory-indicator" class:active={$memoryAccessActive}>
    <div class="icon">
        <!-- Brain icon SVG -->
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path 
                d="M12 3C7.03 3 3 7.03 3 12s4.03 9 9 9 9-4.03 9-9-4.03-9-9-9z" 
                fill="none"
                stroke="currentColor" 
                stroke-width="1.5"
            />
            <path 
                d="M12 3c-2 2.5-2 6 0 9s2 6.5 0 9M3 12h18M5.5 7h13M5.5 17h13" 
                stroke="currentColor" 
                stroke-width="1.5"
                stroke-linecap="round"
            />
        </svg>
    </div>
    
    <div class="info">
        <span class="label">MEMORY</span>
        <span class="status">
            {#if $memoryAccessActive}
                RETRIEVING...
            {:else if $userProfile.name}
                {$memories.length} items
            {:else}
                STANDBY
            {/if}
        </span>
    </div>

    {#if $memoryAccessActive}
        <div class="pulse-ring"></div>
    {/if}
</div>

<style>
    .memory-indicator {
        display: flex;
        align-items: center;
        gap: var(--space-sm);
        padding: var(--space-sm) var(--space-md);
        background: var(--bg-panel);
        border: var(--border-subtle);
        border-radius: 4px;
        position: relative;
        overflow: hidden;
        transition: all var(--transition-normal);
    }

    .memory-indicator.active {
        border-color: var(--success-green);
        box-shadow: 0 0 15px rgba(0, 255, 136, 0.3);
    }

    .icon {
        width: 24px;
        height: 24px;
        color: var(--secondary-blue);
        transition: color var(--transition-fast);
    }

    .active .icon {
        color: var(--success-green);
        animation: pulse-icon 0.5s ease-in-out infinite alternate;
    }

    .info {
        display: flex;
        flex-direction: column;
    }

    .label {
        font-family: var(--font-display);
        font-size: 0.6rem;
        letter-spacing: 0.15em;
        color: var(--text-muted);
    }

    .status {
        font-family: var(--font-mono);
        font-size: 0.7rem;
        color: var(--text-secondary);
    }

    .active .status {
        color: var(--success-green);
    }

    .pulse-ring {
        position: absolute;
        top: 50%;
        left: 24px;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--success-green);
        transform: translate(-50%, -50%);
        animation: pulse-ring 1s ease-out infinite;
    }

    @keyframes pulse-icon {
        from { transform: scale(1); }
        to { transform: scale(1.1); }
    }

    @keyframes pulse-ring {
        0% {
            transform: translate(-50%, -50%) scale(0.5);
            opacity: 1;
        }
        100% {
            transform: translate(-50%, -50%) scale(3);
            opacity: 0;
        }
    }
</style>
