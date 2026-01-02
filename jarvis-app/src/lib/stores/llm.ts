/**
 * LLM State Store
 * Tracks the global status of the LLM engine for UI synchronization
 */
import { writable } from 'svelte/store';

export type LlmStatus = 'PENDING' | 'LOADING' | 'READY' | 'ERROR';

export const llmStatus = writable<LlmStatus>('PENDING');
export const modelName = writable<string>('');
