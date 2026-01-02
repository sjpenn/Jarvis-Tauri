<!--
  ChatInterface.svelte - Main chat UI with streaming support
-->
<script lang="ts">
    import {
        messages,
        currentResponse,
        isProcessing,
        sendMessage,
        startStreamingChat,
    } from "$lib/stores/chat";
    import { memoryAccessActive } from "$lib/stores/memory";
    import MarkdownMessage from "./MarkdownMessage.svelte";
    import { afterUpdate, tick } from "svelte";

    let inputValue = "";
    let messagesEl: HTMLDivElement;
    let ttsEnabled = false;
    let lastSpokenId = "";

    async function handleSubmit() {
        if (!inputValue.trim() || $isProcessing) return;

        const message = inputValue;
        inputValue = "";
        await startStreamingChat(message); // Use streaming
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    }

    // Auto-scroll to bottom
    afterUpdate(() => {
        if (messagesEl) {
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }
    });

    // TTS Logic
    $: if (ttsEnabled && $messages.length > 0) {
        const lastMsg = $messages[$messages.length - 1];
        if (
            lastMsg.role === "assistant" &&
            lastMsg.id !== lastSpokenId &&
            !$isProcessing
        ) {
            lastSpokenId = lastMsg.id;
            speak(lastMsg.content);
        }
    }

    function speak(text: string) {
        if (!window.speechSynthesis) return;

        // Cancel any current speech
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        // Select a voice if needed, or stick to default
        // const voices = window.speechSynthesis.getVoices();
        // utterance.voice = voices.find(v => v.name.includes("Google US English")) || null;

        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
    }

    function toggleTTS() {
        ttsEnabled = !ttsEnabled;
        if (!ttsEnabled) {
            window.speechSynthesis.cancel();
        }
    }
</script>

<div class="chat-interface panel">
    <div class="panel-header">
        <span>JARVIS INTERFACE</span>
        <div class="header-controls">
            <button
                class="icon-btn"
                class:active={ttsEnabled}
                on:click={toggleTTS}
                title={ttsEnabled ? "Disable Voice" : "Enable Voice"}
            >
                {ttsEnabled ? "🔊" : "🔇"}
            </button>
            {#if $isProcessing}
                <span class="processing-indicator">PROCESSING...</span>
            {/if}
        </div>
    </div>

    <div class="messages" bind:this={messagesEl}>
        {#if $messages.length === 0}
            <div class="welcome">
                <div class="welcome-icon">J</div>
                <p>
                    Hello. I am <strong>JARVIS</strong>, your personal
                    assistant.
                </p>
                <p class="hint">How may I assist you today?</p>
            </div>
        {/if}

        {#each $messages as msg (msg.id)}
            <div
                class="message {msg.role}"
                class:has-context={msg.memoryContextUsed}
            >
                <div class="message-content">
                    <MarkdownMessage content={msg.content} />
                </div>
                {#if msg.memoriesRetrieved && msg.memoriesRetrieved > 0}
                    <div class="context-badge">
                        <span class="memory-icon">🧠</span>
                        {msg.memoriesRetrieved} memories used
                    </div>
                {/if}
            </div>
        {/each}

        {#if $currentResponse}
            <div class="message assistant streaming">
                <div class="message-content">
                    {$currentResponse}<span class="cursor">▊</span>
                </div>
            </div>
        {/if}
    </div>

    <div class="input-area">
        <input
            type="text"
            class="input"
            placeholder="Speak freely..."
            bind:value={inputValue}
            on:keydown={handleKeydown}
            disabled={$isProcessing}
        />
        <button
            class="btn btn-primary send-btn"
            on:click={handleSubmit}
            disabled={$isProcessing || !inputValue.trim()}
        >
            {#if $isProcessing}
                <span class="spinner"></span>
            {:else}
                SEND
            {/if}
        </button>
    </div>
</div>

<style>
    .chat-interface {
        display: flex;
        flex-direction: column;
        height: 100%;
        min-height: 400px;
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

    .header-controls {
        display: flex;
        align-items: center;
        gap: var(--space-md);
    }

    .icon-btn {
        background: transparent;
        border: none;
        cursor: pointer;
        padding: 4px;
        border-radius: 4px;
        transition: all 0.2s ease;
        opacity: 0.7;
        font-size: 1rem;
    }

    .icon-btn:hover {
        opacity: 1;
        background: rgba(255, 255, 255, 0.1);
    }

    .icon-btn.active {
        opacity: 1;
        text-shadow: 0 0 10px var(--primary-blue);
    }

    .processing-indicator {
        color: var(--warning-yellow);
        animation: blink 1s infinite;
    }

    .messages {
        flex: 1;
        overflow-y: auto;
        padding: var(--space-md);
        display: flex;
        flex-direction: column;
        gap: var(--space-md);
    }

    .welcome {
        text-align: center;
        padding: var(--space-xl);
        color: var(--text-secondary);
    }

    .welcome-icon {
        width: 60px;
        height: 60px;
        margin: 0 auto var(--space-md);
        background: linear-gradient(
            135deg,
            var(--tertiary-blue),
            var(--secondary-blue)
        );
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-display);
        font-size: 1.5rem;
        color: var(--primary-blue);
        box-shadow: var(--glow-sm);
    }

    .welcome .hint {
        font-size: 0.85rem;
        color: var(--text-muted);
        margin-top: var(--space-sm);
    }

    .message {
        max-width: 85%;
        animation: fade-in 0.2s ease-out;
    }

    .message.user {
        align-self: flex-end;
    }

    .message.assistant {
        align-self: flex-start;
    }

    .message-content {
        padding: var(--space-sm) var(--space-md);
        border-radius: 8px;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    .user .message-content {
        background: linear-gradient(
            135deg,
            var(--tertiary-blue),
            var(--secondary-blue)
        );
        color: var(--text-primary);
    }

    .assistant .message-content {
        background: var(--bg-panel-solid);
        border: var(--border-subtle);
        color: var(--text-secondary);
    }

    .streaming .cursor {
        animation: blink 0.5s step-end infinite;
        color: var(--primary-blue);
    }

    .context-badge {
        margin-top: var(--space-xs);
        font-size: 0.7rem;
        color: var(--success-green);
        display: flex;
        align-items: center;
        gap: 4px;
    }

    .input-area {
        display: flex;
        gap: var(--space-sm);
        padding: var(--space-md);
        border-top: var(--border-subtle);
    }

    .input-area .input {
        flex: 1;
    }

    .send-btn {
        min-width: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .spinner {
        width: 16px;
        height: 16px;
        border: 2px solid var(--primary-blue);
        border-top-color: transparent;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }

    @keyframes fade-in {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes blink {
        50% {
            opacity: 0;
        }
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }
</style>
