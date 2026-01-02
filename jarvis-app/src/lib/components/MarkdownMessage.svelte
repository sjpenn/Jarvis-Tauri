<!--
  MarkdownMessage.svelte - Rich markdown renderer for chat messages
  Supports tables, code blocks, alerts, and basic formatting
-->
<script lang="ts">
    import { onMount } from "svelte";
    import { marked } from "marked";

    export let content: string;

    let htmlContent: string = "";

    // Configure marked for GitHub-flavored markdown
    marked.setOptions({
        gfm: true, // GitHub Flavored Markdown
        breaks: true, // Convert \n to <br>
        headerIds: false, // Don't add IDs to headers
    });

    // Custom renderer for alerts (GitHub-style)
    function processAlerts(markdown: string): string {
        // Process alerts: > [!NOTE], > [!WARNING], etc.
        return markdown
            .replace(
                /^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]/gm,
                (match, type) => {
                    const lowerType = type.toLowerCase();
                    return `<div class="alert alert-${lowerType}"><strong>${type}</strong>`;
                },
            )
            .replace(/^>(?!\s*\[!)/gm, ""); // Remove remaining > for alert content
    }

    // Render markdown to HTML
    function renderMarkdown(md: string): string {
        try {
            // Preprocess for alerts
            const processed = processAlerts(md);

            // Convert markdown to HTML
            let html = marked.parse(processed) as string;

            // Post-process: wrap tables in container
            html = html.replace(
                /<table>/g,
                '<div class="table-wrapper"><table>',
            );
            html = html.replace(/<\/table>/g, "</table></div>");

            // Close alert divs
            html = html.replace(
                /(<div class="alert alert-\w+">.*?)(<\/blockquote>|$)/gs,
                "$1</div>",
            );

            return html;
        } catch (e) {
            console.error("Markdown rendering error:", e);
            return `<p>${md}</p>`;
        }
    }

    $: htmlContent = renderMarkdown(content);
</script>

<div class="markdown-content" bind:innerHTML={htmlContent}></div>

<style>
    .markdown-content {
        color: var(--text-secondary);
        line-height: 1.6;
    }

    /* Headers */
    .markdown-content :global(h1),
    .markdown-content :global(h2),
    .markdown-content :global(h3) {
        color: var(--primary-blue);
        font-family: var(--font-display);
        margin: var(--space-md) 0 var(--space-sm) 0;
        font-weight: 600;
    }

    .markdown-content :global(h1) {
        font-size: 1.4rem;
    }
    .markdown-content :global(h2) {
        font-size: 1.2rem;
    }
    .markdown-content :global(h3) {
        font-size: 1rem;
    }

    /* Paragraphs */
    .markdown-content :global(p) {
        margin: var(--space-sm) 0;
    }

    /* Bold and Italic */
    .markdown-content :global(strong) {
        color: var(--primary-blue);
        font-weight: 600;
    }

    .markdown-content :global(em) {
        color: var(--secondary-blue);
        font-style: italic;
    }

    /* Links */
    .markdown-content :global(a) {
        color: var(--tertiary-blue);
        text-decoration: underline;
        transition: color 0.2s;
    }

    .markdown-content :global(a:hover) {
        color: var(--primary-blue);
    }

    /* Tables */
    .markdown-content :global(.table-wrapper) {
        overflow-x: auto;
        margin: var(--space-md) 0;
        border-radius: 4px;
        border: var(--border-subtle);
    }

    .markdown-content :global(table) {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
        background: var(--bg-panel-solid);
    }

    .markdown-content :global(th) {
        background: linear-gradient(
            135deg,
            var(--tertiary-blue),
            var(--secondary-blue)
        );
        color: var(--text-primary);
        font-weight: 600;
        padding: var(--space-sm) var(--space-md);
        text-align: left;
        border-bottom: 1px solid var(--primary-blue);
    }

    .markdown-content :global(td) {
        padding: var(--space-sm) var(--space-md);
        border-bottom: 1px solid rgba(0, 243, 255, 0.1);
    }

    .markdown-content :global(tr:last-child td) {
        border-bottom: none;
    }

    .markdown-content :global(tr:hover) {
        background: rgba(0, 243, 255, 0.05);
    }

    /* Code blocks */
    .markdown-content :global(code) {
        background: rgba(0, 0, 0, 0.3);
        padding: 2px 6px;
        border-radius: 3px;
        font-family: "Courier New", monospace;
        font-size: 0.85em;
        color: var(--success-green);
    }

    .markdown-content :global(pre) {
        background: rgba(0, 0, 0, 0.4);
        padding: var(--space-md);
        border-radius: 6px;
        overflow-x: auto;
        margin: var(--space-md) 0;
        border: 1px solid rgba(0, 243, 255, 0.2);
    }

    .markdown-content :global(pre code) {
        background: none;
        padding: 0;
        color: var(--text-secondary);
    }

    /* Lists */
    .markdown-content :global(ul),
    .markdown-content :global(ol) {
        margin: var(--space-sm) 0;
        padding-left: var(--space-lg);
    }

    .markdown-content :global(li) {
        margin: var(--space-xs) 0;
    }

    /* Alerts (GitHub-style) */
    .markdown-content :global(.alert) {
        padding: var(--space-md);
        margin: var(--space-md) 0;
        border-radius: 6px;
        border-left: 4px solid;
    }

    .markdown-content :global(.alert strong) {
        display: block;
        margin-bottom: var(--space-xs);
    }

    .markdown-content :global(.alert-note) {
        background: rgba(0, 112, 243, 0.1);
        border-color: var(--secondary-blue);
    }

    .markdown-content :global(.alert-tip) {
        background: rgba(0, 200, 83, 0.1);
        border-color: var(--success-green);
    }

    .markdown-content :global(.alert-important) {
        background: rgba(130, 80, 223, 0.1);
        border-color: #8250df;
    }

    .markdown-content :global(.alert-warning) {
        background: rgba(255, 174, 0, 0.1);
        border-color: var(--warning-yellow);
    }

    .markdown-content :global(.alert-caution) {
        background: rgba(255, 42, 42, 0.1);
        border-color: var(--alert-red);
    }

    /* Blockquotes */
    .markdown-content :global(blockquote) {
        border-left: 3px solid var(--tertiary-blue);
        padding-left: var(--space-md);
        margin: var(--space-md) 0;
        color: var(--text-muted);
        font-style: italic;
    }

    /* Horizontal rule */
    .markdown-content :global(hr) {
        border: none;
        border-top: 1px solid rgba(0, 243, 255, 0.2);
        margin: var(--space-lg) 0;
    }
</style>
