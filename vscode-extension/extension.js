const vscode = require('vscode');

/* ─── конфигурация ───────────────────────────────────── */

const CONFIG_SECTION = 'explainMarketplaceCode';

function getConfig(key) {
    return vscode.workspace.getConfiguration(CONFIG_SECTION).get(key);
}

async function setConfig(key, value) {
    const target = vscode.ConfigurationTarget.Global;
    await vscode.workspace.getConfiguration(CONFIG_SECTION).update(key, value, target);
}

/* ─── activate ───────────────────────────────────────── */

function activate(context) {
    const commands = [
        vscode.commands.registerCommand('explainMarketplaceCode', explainMarketplaceCode),
        vscode.commands.registerCommand('explainMarketplaceCode.setApiKey', setApiKey),
        vscode.commands.registerCommand('explainMarketplaceCode.setDefaultPrompt', setDefaultPrompt),
    ];
    context.subscriptions.push(...commands);
}

/* ─── основная команда ───────────────────────────────── */

async function explainMarketplaceCode() {
    // 1. Получить код из редактора
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('Откройте файл с кодом маркетплейса.');
        return;
    }

    const selection = editor.selection;
    const code = selection.isEmpty
        ? editor.document.getText()
        : editor.document.getText(selection);

    if (!code.trim()) {
        vscode.window.showWarningMessage('Нет кода для объяснения.');
        return;
    }

    const fileName = editor.document.fileName;

    // 2. Проверить / запросить API-ключ
    let apiKey = getConfig('apiKey');
    if (!apiKey) {
        apiKey = await vscode.window.showInputBox({
            prompt: 'Введите OpenAI API-ключ (он будет сохранён в настройках)',
            password: true,
            placeHolder: 'sk-...',
            ignoreFocusOut: true,
        });
        if (!apiKey) return;
        await setConfig('apiKey', apiKey);
        vscode.window.showInformationMessage('API-ключ сохранён в настройках.');
    }

    // 3. InputBox для промпта
    const defaultPrompt = getConfig('defaultPrompt')
        || 'Объясни этот код в контексте платформы маркетплейса';

    const prompt = await vscode.window.showInputBox({
        prompt: 'Введите промпт для объяснения кода',
        value: defaultPrompt,
        placeHolder: 'Объясни этот код...',
        ignoreFocusOut: true,
    });
    if (prompt === undefined) return;

    // 4. Отправить запрос к OpenAI
    vscode.window.showInformationMessage('⏳ Запрашиваю объяснение у OpenAI...');

    let explanation;
    try {
        explanation = await callOpenAI(apiKey, prompt, code, fileName);
    } catch (err) {
        vscode.window.showErrorMessage(
            `Ошибка OpenAI: ${err.message ?? 'неизвестная ошибка'}`
        );
        return;
    }

    // 5. Показать результат
    showExplanationPanel(explanation, fileName, prompt);
}

/* ─── OpenAI API ─────────────────────────────────────── */

async function callOpenAI(apiKey, userPrompt, code, fileName) {
    const endpoint = getConfig('endpoint') || 'https://api.openai.com/v1';
    const model    = getConfig('model')    || 'gpt-4o-mini';

    const messages = [
        {
            role: 'system',
            content: [
                'Ты — ассистент по курсу «Методы и технологии программирования».',
                'Студент разрабатывает учебный маркетплейс на FastAPI + PostgreSQL.',
                'Отвечай подробно, но по делу. Используй примеры кода, где уместно.',
                'Форматируй ответ в Markdown.',
            ].join('\n'),
        },
        {
            role: 'user',
            content: [
                userPrompt,
                '',
                `Файл: ${fileName}`,
                '```' + (fileName.split('.').pop()),
                code,
                '```',
            ].join('\n'),
        },
    ];

    const response = await fetch(`${endpoint}/chat/completions`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
            model,
            messages,
            temperature: 0.3,
            max_tokens: 4096,
        }),
    });

    if (!response.ok) {
        const body = await response.text();
        throw new Error(`${response.status} ${response.statusText} — ${body}`);
    }

    const data = await response.json();
    return data.choices?.[0]?.message?.content || 'Пустой ответ от модели.';
}

/* ─── вспомогательные команды ────────────────────────── */

async function setApiKey() {
    const key = await vscode.window.showInputBox({
        prompt: 'Введите OpenAI API-ключ',
        password: true,
        placeHolder: 'sk-...',
        ignoreFocusOut: true,
    });
    if (key) {
        await setConfig('apiKey', key);
        vscode.window.showInformationMessage('✅ API-ключ сохранён.');
    }
}

async function setDefaultPrompt() {
    const current = getConfig('defaultPrompt') || 'Объясни этот код в контексте платформы маркетплейса';
    const prompt = await vscode.window.showInputBox({
        prompt: 'Введите промпт по умолчанию для объяснения кода',
        value: current,
        placeHolder: 'Объясни этот код...',
        ignoreFocusOut: true,
        valueSelection: undefined,
    });
    if (prompt !== undefined) {
        await setConfig('defaultPrompt', prompt);
        vscode.window.showInformationMessage('✅ Промпт по умолчанию сохранён.');
    }
}

/* ─── webview-панель ─────────────────────────────────── */

function showExplanationPanel(content, fileName, promptUsed) {
    const panel = vscode.window.createWebviewPanel(
        'marketplaceExplanation',
        'Marketplace Code Explanation',
        vscode.ViewColumn.Beside,
        { enableScripts: false }
    );

    const html = `<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Explain Marketplace Code</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 16px 20px;
            line-height: 1.6;
            color: var(--vscode-editor-foreground);
            background: var(--vscode-editor-background);
        }
        h2, h3 {
            border-bottom: 1px solid var(--vscode-panel-border);
            padding-bottom: 6px;
            margin-top: 24px;
        }
        code {
            background: var(--vscode-textBlockQuote-background);
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }
        pre {
            background: var(--vscode-textBlockQuote-background);
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
        }
        pre code { background: none; padding: 0; }
        blockquote {
            border-left: 3px solid var(--vscode-textLink-foreground);
            margin: 12px 0;
            padding: 8px 12px;
            background: var(--vscode-textBlockQuote-background);
        }
        hr { border: none; border-top: 1px solid var(--vscode-panel-border); }
        .meta {
            font-size: 0.85em;
            opacity: 0.7;
            margin-bottom: 16px;
        }
        ul, ol { padding-left: 24px; }
        table { border-collapse: collapse; width: 100%; }
        th, td {
            border: 1px solid var(--vscode-panel-border);
            padding: 6px 10px;
            text-align: left;
        }
        th { background: var(--vscode-textBlockQuote-background); }
    </style>
</head>
<body>
    <p class="meta">
        <strong>Файл:</strong> <code>${escapeHtml(fileName)}</code><br>
        <strong>Промпт:</strong> <em>${escapeHtml(promptUsed)}</em>
    </p>
    <hr>
    ${renderMarkdown(content)}
</body>
</html>`;

    panel.webview.html = html;
}

/* ─── helpers ─────────────────────────────────────────── */

function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function renderMarkdown(md) {
    const lines = md.split('\n');
    const out = [];
    let inCodeBlock = false;

    for (let line of lines) {
        if (line.startsWith('```')) {
            if (inCodeBlock) {
                out.push('</code></pre>');
                inCodeBlock = false;
            } else {
                out.push('<pre><code>');
                inCodeBlock = true;
            }
            continue;
        }

        if (inCodeBlock) {
            out.push(escapeHtml(line));
            continue;
        }

        const trimmed = line.trim();

        if (trimmed.startsWith('### ')) {
            out.push(`<h3>${escapeHtml(trimmed.slice(4))}</h3>`);
        } else if (trimmed.startsWith('## ')) {
            out.push(`<h2>${escapeHtml(trimmed.slice(3))}</h2>`);
        } else if (trimmed.startsWith('> ')) {
            out.push(`<blockquote>${escapeHtml(trimmed.slice(2))}</blockquote>`);
        } else if (trimmed.startsWith('- ')) {
            out.push(`<li>${escapeHtml(trimmed.slice(2))}</li>`);
        } else if (/^\d+\.\s/.test(trimmed)) {
            out.push(`<li>${escapeHtml(trimmed.replace(/^\d+\.\s*/, ''))}</li>`);
        } else if (trimmed.startsWith('|')) {
            // простая табличная строка — оставляем как есть
            out.push(`<p>${escapeHtml(trimmed)}</p>`);
        } else if (trimmed === '') {
            out.push('<br>');
        } else {
            out.push(`<p>${escapeHtml(trimmed)}</p>`);
        }
    }

    if (inCodeBlock) {
        out.push('</code></pre>');
    }

    return out.join('\n');
}

module.exports = { activate };
