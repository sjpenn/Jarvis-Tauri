/**
 * Memory stores - for user preferences and semantic memory
 * This data uses the vector store for context-aware retrieval
 */

import { writable } from 'svelte/store';

// Types
export interface UserProfile {
    name: string | null;
    facts: string[];
    created_at: string | null;
    updated_at: string | null;
}

export interface Preference {
    category: string;
    key: string;
    value: string;
    created_at: string | null;
}

export interface Memory {
    id: number;
    content: string;
    category: string;
    importance: number;
    created_at: string | null;
    last_accessed: string | null;
}

// Memory access indicator - glows when vector store is being queried
export const memoryAccessActive = writable(false);

// User profile
export const userProfile = writable<UserProfile>({
    name: null,
    facts: [],
    created_at: null,
    updated_at: null
});

// All preferences
export const preferences = writable<Preference[]>([]);

// Recent/relevant memories
export const memories = writable<Memory[]>([]);

// Memory context for LLM
export const memoryContext = writable<string>('');

/**
 * Fetch user profile from Rust backend
 */
export async function loadUserProfile() {
    try {
        const { invoke } = await import('@tauri-apps/api/core');
        const profile = await invoke<UserProfile>('get_user_profile');
        userProfile.set(profile);
        return profile;
    } catch (error) {
        console.error('Failed to load user profile:', error);
        return null;
    }
}

/**
 * Set user name
 */
export async function setUserName(name: string) {
    try {
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('set_user_name', { name });
        userProfile.update(p => ({ ...p, name }));
    } catch (error) {
        console.error('Failed to set user name:', error);
    }
}

/**
 * Add a memory
 */
export async function saveMemory(content: string, category: string = 'general', importance: number = 5) {
    try {
        const { invoke } = await import('@tauri-apps/api/core');
        memoryAccessActive.set(true);

        const id = await invoke<number>('add_memory', { content, category, importance });

        // Add to local store
        memories.update(m => [...m, {
            id,
            content,
            category,
            importance,
            created_at: new Date().toISOString(),
            last_accessed: null
        }]);

        memoryAccessActive.set(false);
        return id;
    } catch (error) {
        console.error('Failed to save memory:', error);
        memoryAccessActive.set(false);
        return null;
    }
}

/**
 * Search memories
 */
export async function searchMemories(query: string, limit: number = 10) {
    try {
        const { invoke } = await import('@tauri-apps/api/core');
        memoryAccessActive.set(true);

        const results = await invoke<Memory[]>('search_memories', { query, limit });
        memories.set(results);

        memoryAccessActive.set(false);
        return results;
    } catch (error) {
        console.error('Failed to search memories:', error);
        memoryAccessActive.set(false);
        return [];
    }
}

/**
 * Get full memory context for LLM system prompt
 */
export async function loadMemoryContext() {
    try {
        const { invoke } = await import('@tauri-apps/api/core');
        memoryAccessActive.set(true);

        const context = await invoke<string>('get_memory_context');
        memoryContext.set(context);

        memoryAccessActive.set(false);
        return context;
    } catch (error) {
        console.error('Failed to load memory context:', error);
        memoryAccessActive.set(false);
        return '';
    }
}

/**
 * Load all preferences
 */
export async function loadPreferences() {
    try {
        const { invoke } = await import('@tauri-apps/api/core');
        const prefs = await invoke<Preference[]>('get_all_preferences');
        preferences.set(prefs);
        return prefs;
    } catch (error) {
        console.error('Failed to load preferences:', error);
        return [];
    }
}

/**
 * Set a preference
 */
export async function setPreference(category: string, key: string, value: string) {
    try {
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('set_preference', { category, key, value });

        preferences.update(prefs => {
            const existing = prefs.findIndex(p => p.category === category && p.key === key);
            const newPref = { category, key, value, created_at: new Date().toISOString() };
            if (existing >= 0) {
                prefs[existing] = newPref;
                return [...prefs];
            }
            return [...prefs, newPref];
        });
    } catch (error) {
        console.error('Failed to set preference:', error);
    }
}
