<!--
  ModelSettings.svelte - Configure Phi-3 model path
-->
<script lang="ts">
    import { invoke } from "@tauri-apps/api/core";
    import { open } from "@tauri-apps/plugin-dialog";
    import { llmStatus, modelName } from "$lib/stores/llm";

    let modelPath = "";
    let systemPrompt = "You are JARVIS, a helpful AI assistant.";
    let status = "";
    let isLoading = false;

    // Load saved preferences on mount
    import { onMount } from "svelte";
    onMount(async () => {
        try {
            const prefs = await invoke("get_all_preferences");
            const sp = (prefs as any[]).find(
                (p) => p.category === "llm" && p.key === "system_prompt",
            );
            if (sp) systemPrompt = sp.value;
        } catch (e) {
            console.error("Failed to load prefs", e);
        }
    });

    async function selectModelFile() {
        try {
            const selected = await open({
                multiple: false,
                filters: [
                    {
                        name: "GGUF Model",
                        extensions: ["gguf"],
                    },
                ],
            });

            if (selected) {
                modelPath = selected as string;
            }
        } catch (error) {
            console.error("Error selecting file:", error);
            status = `Error: ${error}`;
        }
    }

    async function saveSettings() {
        isLoading = true;
        status = "Saving settings...";

        try {
            // Save System Prompt
            await invoke("set_preference", {
                category: "llm",
                key: "system_prompt",
                value: systemPrompt,
            });

            // Load Model if path is provided
            if (modelPath) {
                llmStatus.set("LOADING");
                await invoke("set_model_path", { path: modelPath });
                modelName.set(
                    modelPath.split(/[\\/]/).pop() || "Unknown Model",
                );
            }

            status = "✓ Settings saved & Model loaded!";
            llmStatus.set("READY");
        } catch (error) {
            status = `✗ Error: ${error}`;
            llmStatus.set("ERROR");
        } finally {
            isLoading = false;
        }
    }
</script>

<div class="model-settings panel">
    <div class="panel-header">PHI-3 CONFIGURATION</div>
    <div class="panel-content">
        <p class="hint">
            Download Phi-3 Mini GGUF from
            <a
                href="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf"
                target="_blank"
            >
                Hugging Face
            </a>
        </p>

        <div class="setting-group">
            <label class="label">Model Path</label>
            <div class="file-selector">
                <input
                    type="text"
                    class="input"
                    placeholder="No model selected"
                    bind:value={modelPath}
                    readonly
                />
                <button class="btn" on:click={selectModelFile}> Browse </button>
            </div>
        </div>

        <div class="setting-group">
            <label class="label">System Prompt (Persona)</label>
            <textarea
                class="input textarea"
                bind:value={systemPrompt}
                rows="3"
                placeholder="You are JARVIS..."
            ></textarea>
        </div>

        <button
            class="btn btn-primary"
            on:click={saveSettings}
            disabled={isLoading}
        >
            {isLoading ? "Saving..." : "Save & Load"}
        </button>

        {#if status}
            <div
                class="status"
                class:success={status.startsWith("✓")}
                class:error={status.startsWith("✗")}
            >
                {status}
            </div>
        {/if}
    </div>
</div>

<style>
    .model-settings {
        margin-top: var(--space-md);
    }

    .setting-group {
        margin-bottom: var(--space-md);
    }

    .label {
        display: block;
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-bottom: var(--space-xs);
        letter-spacing: 0.05em;
    }

    .textarea {
        width: 100%;
        resize: vertical;
        font-family: var(--font-mono);
        font-size: 0.85rem;
        min-height: 80px;
    }

    .hint {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-bottom: var(--space-md);
        line-height: 1.5;
    }

    .hint a {
        color: var(--primary-blue);
        text-decoration: none;
    }

    .hint a:hover {
        text-decoration: underline;
    }

    .file-selector {
        display: flex;
        gap: var(--space-sm);
    }

    .file-selector .input {
        flex: 1;
    }

    .status {
        margin-top: var(--space-md);
        padding: var(--space-sm);
        border-radius: 4px;
        font-size: 0.8rem;
        text-align: center;
    }

    .status.success {
        background: rgba(0, 255, 136, 0.1);
        color: var(--success-green);
        border: 1px solid var(--success-green);
    }

    .status.error {
        background: rgba(255, 42, 42, 0.1);
        color: var(--alert-red);
        border: 1px solid var(--alert-red);
    }
</style>
