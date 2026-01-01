<!--
  ModelSettings.svelte - Configure Phi-3 model path
-->
<script lang="ts">
    import { invoke } from "@tauri-apps/api/core";
    import { open } from "@tauri-apps/plugin-dialog";

    let modelPath = "";
    let status = "";
    let isLoading = false;

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

    async function setModel() {
        if (!modelPath) {
            status = "Please select a model file first";
            return;
        }

        isLoading = true;
        status = "Loading model...";

        try {
            await invoke("set_model_path", { path: modelPath });
            status = "✓ Model loaded successfully!";
        } catch (error) {
            status = `✗ Error: ${error}`;
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

        <button
            class="btn btn-primary"
            on:click={setModel}
            disabled={!modelPath || isLoading}
        >
            {isLoading ? "Loading..." : "Load Model"}
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
        margin-bottom: var(--space-md);
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
