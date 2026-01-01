/**
 * Chat stores - for conversation and AI responses
 */

import { writable } from 'svelte/store';

// Types
export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: number;
    memoryContextUsed?: boolean;
    memoriesRetrieved?: number;
}

export interface ThoughtLog {
    step: string;
    detail: string;
    timestamp: number;
}

// Chat history
export const messages = writable<ChatMessage[]>([]);

// Current streaming response
export const currentResponse = writable<string>('');

// AI thought process logs
export const thoughtLogs = writable<ThoughtLog[]>([]);

// Is currently processing
export const isProcessing = writable(false);

// Clear thought logs periodically
const MAX_THOUGHT_LOGS = 20;

/**
 * Send a chat message
 */
export async function sendMessage(content: string) {
    if (!content.trim()) return;

    const { invoke } = await import('@tauri-apps/api/core');

    // Add user message
    const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        timestamp: Date.now()
    };
    messages.update(m => [...m, userMessage]);

    isProcessing.set(true);
    currentResponse.set('');

    try {
        // Call Rust backend
        const response = await invoke<{
            message: string;
            memory_context_used: boolean;
            memories_retrieved: number;
        }>('chat', { message: content });

        // Add assistant response
        const assistantMessage: ChatMessage = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: response.message,
            timestamp: Date.now(),
            memoryContextUsed: response.memory_context_used,
            memoriesRetrieved: response.memories_retrieved
        };
        messages.update(m => [...m, assistantMessage]);

    } catch (error) {
        console.error('Chat error:', error);

        // Add error message
        const errorMessage: ChatMessage = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: `Error: ${error}`,
            timestamp: Date.now()
        };
        messages.update(m => [...m, errorMessage]);
    } finally {
        isProcessing.set(false);
    }
}

/**
 * Start streaming chat (for real-time token updates)
 */
export async function startStreamingChat(content: string) {
    if (!content.trim()) return;

    const { invoke } = await import('@tauri-apps/api/core');
    const { listen } = await import('@tauri-apps/api/event');

    // Add user message
    const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        timestamp: Date.now()
    };
    messages.update(m => [...m, userMessage]);

    isProcessing.set(true);
    currentResponse.set('');

    // Set up listeners for streaming
    const tokenListener = await listen<string>('chat:token', (event) => {
        currentResponse.update(r => r + event.payload + ' ');
    });

    const thoughtListener = await listen<ThoughtLog>('chat:thought', (event) => {
        thoughtLogs.update(logs => {
            const newLogs = [...logs, event.payload];
            return newLogs.slice(-MAX_THOUGHT_LOGS);
        });
    });

    const completeListener = await listen('chat:complete', () => {
        // Move streaming response to messages
        currentResponse.subscribe(r => {
            if (r) {
                const assistantMessage: ChatMessage = {
                    id: crypto.randomUUID(),
                    role: 'assistant',
                    content: r.trim(),
                    timestamp: Date.now()
                };
                messages.update(m => [...m, assistantMessage]);
            }
        })();

        currentResponse.set('');
        isProcessing.set(false);

        // Cleanup listeners
        tokenListener();
        thoughtListener();
        completeListener();
    });

    try {
        await invoke('start_chat_stream', { message: content });
    } catch (error) {
        console.error('Streaming chat error:', error);
        isProcessing.set(false);
        tokenListener();
        thoughtListener();
        completeListener();
    }
}

/**
 * Clear chat history
 */
export function clearChat() {
    messages.set([]);
    thoughtLogs.set([]);
    currentResponse.set('');
}
