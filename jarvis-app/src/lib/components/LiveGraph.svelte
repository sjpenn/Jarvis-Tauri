<!--
  LiveGraph.svelte - Real-time CPU/RAM graph
  Binds to Svelte stores (NOT vector store) for instant updates
-->
<script lang="ts">
    import { cpuHistory, memoryHistory } from '$lib/stores/sensors';
    import { onMount } from 'svelte';

    export let title: string = 'System';
    export let type: 'cpu' | 'memory' = 'cpu';
    export let height: number = 60;

    let canvasEl: HTMLCanvasElement;
    let ctx: CanvasRenderingContext2D | null = null;

    $: history = type === 'cpu' ? $cpuHistory : $memoryHistory;
    $: currentValue = history[history.length - 1] ?? 0;
    $: color = type === 'cpu' ? '#00f3ff' : '#007cc2';

    function drawGraph(data: number[]) {
        if (!ctx || !canvasEl) return;

        const width = canvasEl.width;
        const h = canvasEl.height;

        // Clear
        ctx.clearRect(0, 0, width, h);

        if (data.length < 2) return;

        // Draw grid lines
        ctx.strokeStyle = 'rgba(0, 100, 130, 0.2)';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = (h / 4) * i;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }

        // Draw data line
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();

        const step = width / (data.length - 1);
        data.forEach((value, i) => {
            const x = i * step;
            const y = h - (value / 100) * h;
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.stroke();

        // Draw gradient fill
        const gradient = ctx.createLinearGradient(0, 0, 0, h);
        gradient.addColorStop(0, `${color}33`);
        gradient.addColorStop(1, 'transparent');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        data.forEach((value, i) => {
            const x = i * step;
            const y = h - (value / 100) * h;
            if (i === 0) {
                ctx.moveTo(x, h);
                ctx.lineTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.lineTo(width, h);
        ctx.closePath();
        ctx.fill();
    }

    onMount(() => {
        ctx = canvasEl.getContext('2d');
        // Set canvas resolution
        const dpr = window.devicePixelRatio || 1;
        const rect = canvasEl.getBoundingClientRect();
        canvasEl.width = rect.width * dpr;
        canvasEl.height = rect.height * dpr;
        ctx?.scale(dpr, dpr);
    });

    $: if (ctx) drawGraph(history);
</script>

<div class="live-graph panel">
    <div class="header">
        <span class="title">{title}</span>
        <span class="value" style="color: {color}">{currentValue.toFixed(1)}%</span>
    </div>
    <div class="canvas-container" style="height: {height}px">
        <canvas bind:this={canvasEl} style="width: 100%; height: 100%"></canvas>
    </div>
</div>

<style>
    .live-graph {
        padding: var(--space-sm);
    }

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: var(--space-xs);
    }

    .title {
        font-family: var(--font-display);
        font-size: 0.7rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-muted);
    }

    .value {
        font-family: var(--font-mono);
        font-size: 0.8rem;
        font-weight: 500;
    }

    .canvas-container {
        border-radius: 4px;
        overflow: hidden;
        background: var(--bg-darker);
    }

    canvas {
        display: block;
    }
</style>
