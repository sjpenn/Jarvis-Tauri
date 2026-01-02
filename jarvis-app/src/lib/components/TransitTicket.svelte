<script>
    export let route = {};

    // Helper to format time nicely
    const formatTime = (t) => t;
</script>

<div class="tech-ticket">
    <!-- Header: Summary -->
    <div class="ticket-header">
        <div class="route-summary">
            <span class="time-bold">{formatTime(route.departure_time)}</span>
            <div class="arrow">→</div>
            <span class="time-bold">{formatTime(route.arrival_time)}</span>
        </div>
        <div class="fare-box">{route.fare}</div>
    </div>

    <!-- Divider -->
    <div class="ticket-cut">-- -- -- -- -- -- -- -- -- -- -- -- -- --</div>

    <!-- Timeline Body -->
    <div class="ticket-body">
        {#each route.legs as leg, index}
            <div class="leg-row">
                <!-- Left: Time/Icon Column -->
                <div class="leg-info-col">
                    {#if leg.mode === "Transfer"}
                        <div class="icon-transfer">W</div>
                    {:else}
                        <div
                            class="icon-line"
                            style="color: {leg.color}; border-color: {leg.color}"
                        >
                            {leg.line_name ? leg.line_name.charAt(0) : "?"}
                        </div>
                    {/if}
                </div>

                <!-- Middle: Details Column -->
                <div class="leg-details">
                    <div class="leg-title">
                        {#if leg.mode === "Transfer"}
                            <span style="color: var(--warning-amber)"
                                >{leg.description}</span
                            >
                        {:else}
                            <span style="color: {leg.color}; font-weight:bold"
                                >{leg.line_name}</span
                            >
                            <span class="dimmed"
                                >({leg.stop_start} to {leg.stop_end})</span
                            >
                        {/if}
                    </div>
                    <div class="leg-meta">
                        {leg.duration} mins
                    </div>
                </div>
            </div>

            <!-- Connector Line (Vertical) -->
            {#if index !== route.legs.length - 1}
                <div class="connector-line"></div>
            {/if}
        {/each}
    </div>

    <!-- Footer: Total Duration -->
    <div class="ticket-footer">
        <span class="label">TOTAL DURATION</span>
        <span class="value">{route.duration_minutes} MIN</span>
    </div>
</div>

<style>
    :root {
        --primary-blue: #00f3ff;
        --secondary-blue: #007cc2;
        --alert-red: #ff2a2a;
        --warning-amber: #ffae00;
        --bg-panel: rgba(5, 15, 30, 0.8);
        --font-tech: "Courier New", monospace;
    }

    .tech-ticket {
        border: 1px solid var(--primary-blue);
        background: var(--bg-panel);
        color: var(--primary-blue);
        font-family: var(--font-tech);
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 0 5px rgba(0, 243, 255, 0.2);
        clip-path: polygon(
            10px 0,
            100% 0,
            100% calc(100% - 10px),
            calc(100% - 10px) 100%,
            0 100%,
            0 10px
        );
    }

    /* Header */
    .ticket-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .route-summary {
        font-size: 1.1rem;
        display: flex;
        gap: 10px;
        align-items: center;
    }

    .time-bold {
        font-weight: bold;
        text-shadow: 0 0 5px var(--primary-blue);
    }

    .fare-box {
        border: 1px solid var(--warning-amber);
        color: var(--warning-amber);
        padding: 2px 8px;
        font-weight: bold;
        font-size: 0.9rem;
    }

    /* Divider */
    .ticket-cut {
        text-align: center;
        color: var(--secondary-blue);
        margin: 10px 0;
        letter-spacing: 2px;
        font-size: 0.8rem;
        opacity: 0.7;
    }

    /* Timeline */
    .leg-row {
        display: flex;
        align-items: center;
        margin-bottom: 5px;
    }

    .leg-info-col {
        width: 40px;
        display: flex;
        flex-direction: column;
        align-items: center;
        margin-right: 15px;
    }

    /* Icons */
    .icon-line {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 2px solid currentColor;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 0.7rem;
        background: rgba(0, 0, 0, 0.5);
    }

    .icon-transfer {
        width: 20px;
        height: 20px;
        background: transparent;
        border: 1px dashed var(--warning-amber);
        color: var(--warning-amber);
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 0.7rem;
        font-weight: bold;
    }

    .connector-line {
        width: 2px;
        height: 15px;
        background: var(--secondary-blue);
        margin-left: 19px; /* Aligned with icon center */
        opacity: 0.5;
        margin-bottom: 5px;
    }

    /* Details */
    .leg-details {
        flex: 1;
    }

    .leg-title {
        font-size: 0.9rem;
        margin-bottom: 2px;
    }

    .dimmed {
        opacity: 0.6;
        font-size: 0.8rem;
    }
    .leg-meta {
        font-size: 0.7rem;
        color: var(--secondary-blue);
    }

    /* Footer */
    .ticket-footer {
        margin-top: 15px;
        padding-top: 10px;
        border-top: 1px dashed var(--secondary-blue);
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
    }

    .label {
        opacity: 0.7;
    }
    .value {
        color: var(--primary-blue);
        font-weight: bold;
    }
</style>
