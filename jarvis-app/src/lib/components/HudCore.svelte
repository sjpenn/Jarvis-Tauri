<!--
  HudCore.svelte - Central animated status element
  Reflects system status with animated rings and glow effects
-->
<script lang="ts">
    import { cpuUsage, memoryPercent, isConnected } from '$lib/stores/sensors';
    import { isProcessing } from '$lib/stores/chat';
    import { memoryAccessActive } from '$lib/stores/memory';
    import { tweened } from 'svelte/motion';
    import { cubicOut } from 'svelte/easing';

    // Smooth animations
    const cpu = tweened(0, { duration: 500, easing: cubicOut });
    const mem = tweened(0, { duration: 500, easing: cubicOut });

    $: cpu.set($cpuUsage);
    $: mem.set($memoryPercent);

    // Status calculations
    $: overallStatus = $isProcessing ? 'processing' : 
                       $memoryAccessActive ? 'memory' :
                       !$isConnected ? 'offline' : 'active';

    $: statusColor = overallStatus === 'offline' ? 'var(--alert-red)' :
                     overallStatus === 'processing' ? 'var(--warning-yellow)' :
                     overallStatus === 'memory' ? 'var(--success-green)' :
                     'var(--primary-blue)';
</script>

<div class="hud-core" class:processing={$isProcessing} class:memory-active={$memoryAccessActive}>
    <!-- Outer rotating ring -->
    <div class="ring ring-outer" style="--ring-color: {statusColor}">
        <svg viewBox="0 0 200 200">
            <circle cx="100" cy="100" r="95" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="4 8" />
        </svg>
    </div>

    <!-- Middle ring with CPU indicator -->
    <div class="ring ring-middle">
        <svg viewBox="0 0 200 200">
            <circle 
                cx="100" cy="100" r="80" 
                fill="none" 
                stroke="var(--secondary-blue)" 
                stroke-width="3"
                stroke-opacity="0.3"
            />
            <circle 
                cx="100" cy="100" r="80" 
                fill="none" 
                stroke="var(--primary-blue)" 
                stroke-width="3"
                stroke-dasharray="{$cpu * 5.03} 503"
                stroke-linecap="round"
                transform="rotate(-90 100 100)"
            />
        </svg>
    </div>

    <!-- Inner ring with Memory indicator -->
    <div class="ring ring-inner">
        <svg viewBox="0 0 200 200">
            <circle 
                cx="100" cy="100" r="60" 
                fill="none" 
                stroke="var(--tertiary-blue)" 
                stroke-width="3"
                stroke-opacity="0.3"
            />
            <circle 
                cx="100" cy="100" r="60" 
                fill="none" 
                stroke="var(--secondary-blue)" 
                stroke-width="3"
                stroke-dasharray="{$mem * 3.77} 377"
                stroke-linecap="round"
                transform="rotate(-90 100 100)"
            />
        </svg>
    </div>

    <!-- Center core -->
    <div class="core" style="--core-glow: {statusColor}">
        <div class="core-inner">
            <span class="status-text">{overallStatus.toUpperCase()}</span>
            <span class="cpu-text">CPU {$cpu.toFixed(0)}%</span>
            <span class="mem-text">MEM {$mem.toFixed(0)}%</span>
        </div>
    </div>
</div>

<style>
    .hud-core {
        position: relative;
        width: 200px;
        height: 200px;
        margin: var(--space-lg) auto;
    }

    .ring {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
    }

    .ring svg {
        width: 100%;
        height: 100%;
    }

    .ring-outer {
        animation: spin-slow 30s linear infinite;
        color: var(--ring-color, var(--primary-blue));
    }

    .ring-middle {
        animation: spin-slow 20s linear infinite reverse;
    }

    .ring-inner {
        animation: spin-slow 15s linear infinite;
    }

    .core {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 100px;
        height: 100px;
        background: var(--bg-panel);
        border-radius: 50%;
        border: 2px solid var(--primary-blue);
        box-shadow: var(--glow-sm), inset 0 0 20px rgba(0, 243, 255, 0.1);
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .processing .core {
        animation: pulse-glow 1s ease-in-out infinite;
    }

    .memory-active .core {
        border-color: var(--success-green);
        box-shadow: 0 0 20px var(--success-green);
    }

    .core-inner {
        text-align: center;
        font-family: var(--font-display);
    }

    .status-text {
        display: block;
        font-size: 0.6rem;
        color: var(--primary-blue);
        letter-spacing: 0.15em;
        margin-bottom: 4px;
    }

    .cpu-text, .mem-text {
        display: block;
        font-size: 0.55rem;
        color: var(--text-muted);
        letter-spacing: 0.1em;
    }

    @keyframes spin-slow {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    @keyframes pulse-glow {
        0%, 100% { box-shadow: var(--glow-sm); }
        50% { box-shadow: var(--glow-lg); }
    }
</style>
