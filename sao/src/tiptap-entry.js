import { Editor, InputRule, Node, renderNestedMarkdownContent } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import { CodeBlockLowlight } from '@tiptap/extension-code-block-lowlight';
import { createLowlight } from 'lowlight';
import python from 'highlight.js/lib/languages/python';
import javascript from 'highlight.js/lib/languages/javascript';
import sql from 'highlight.js/lib/languages/sql';
import xml from 'highlight.js/lib/languages/xml';

const lowlight = createLowlight();
lowlight.register('python', python);
lowlight.register('javascript', javascript);
lowlight.register('sql', sql);
lowlight.register('xml', xml);
import { Markdown } from '@tiptap/markdown';
import { history } from '@tiptap/pm/history';
import { Link } from '@tiptap/extension-link';
import { Table } from '@tiptap/extension-table';
import { TableRow } from '@tiptap/extension-table-row';
import { TableCell } from '@tiptap/extension-table-cell';
import { TableHeader } from '@tiptap/extension-table-header';
import { TaskList } from '@tiptap/extension-task-list';
import { TaskItem } from '@tiptap/extension-task-item';

const History = history;

const MarkdownTable = Table.extend({
    markdownTokenName: 'table',

    parseMarkdown(token, helpers) {
        const headerRow = helpers.createNode('tableRow', {},
            token.header.map(cell =>
                helpers.createNode('tableHeader', {}, [
                    helpers.createNode('paragraph', {}, helpers.parseInline(cell.tokens)),
                ])
            )
        );
        const bodyRows = token.rows.map(row =>
            helpers.createNode('tableRow', {},
                row.map(cell =>
                    helpers.createNode('tableCell', {}, [
                        helpers.createNode('paragraph', {}, helpers.parseInline(cell.tokens)),
                    ])
                )
            )
        );
        return helpers.createNode('table', {}, [headerRow, ...bodyRows]);
    },

    renderMarkdown(node, helpers) {
        const rows = node.content || [];
        const lines = [];
        for (let i = 0; i < rows.length; i++) {
            lines.push(helpers.renderChild(rows[i], i));
            if (i === 0) {
                const cols = (rows[i].content || []).length;
                lines.push('| ' + Array(cols).fill('---').join(' | ') + ' |');
            }
        }
        return lines.join('\n');
    },
});

const MarkdownTableRow = TableRow.extend({
    renderMarkdown(node, helpers) {
        const cells = node.content || [];
        const parts = [];
        for (let i = 0; i < cells.length; i++) {
            parts.push(helpers.renderChild(cells[i], i).trim());
        }
        return '| ' + parts.join(' | ') + ' |';
    },
});

const MarkdownTableCell = TableCell.extend({
    renderMarkdown(node, helpers) {
        return helpers.renderChildren(node.content).trim();
    },
});

const MarkdownTableHeader = TableHeader.extend({
    renderMarkdown(node, helpers) {
        return helpers.renderChildren(node.content).trim();
    },
});

const MarkdownTaskList = TaskList.extend({
    markdownTokenName: 'taskList',

    parseMarkdown(token, helpers) {
        return helpers.createNode(
            'taskList',
            {},
            token.items.map(item => {
                const content = [
                    helpers.createNode('paragraph', {}, helpers.parseInline(item.tokens)),
                ];
                if (item.nestedTokens && item.nestedTokens.length > 0) {
                    content.push(...helpers.parseChildren(item.nestedTokens));
                }
                return helpers.createNode('taskItem', { checked: item.checked || false }, content);
            })
        );
    },

    renderMarkdown(node, helpers) {
        return helpers.renderChildren(node.content, '\n');
    },
});

const MarkdownTaskItem = TaskItem.extend({
    renderMarkdown(node, helpers) {
        const checked = node.attrs && node.attrs.checked;
        const prefix = checked ? '- [x] ' : '- [ ] ';
        return renderNestedMarkdownContent(node, helpers, prefix);
    },
});

const LinkWithInputRule = Link.extend({
    addInputRules() {
        const type = this.type;
        return [
            ...(this.parent?.() ?? []),
            new InputRule({
                find: /\[([^\]]+)\]\(([^)]+)\)$/,
                handler: ({ state, range, match }) => {
                    const { tr } = state;
                    tr.replaceWith(
                        range.from, range.to,
                        state.schema.text(match[1], [type.create({ href: match[2] })])
                    );
                    tr.removeStoredMark(type);
                },
            }),
        ];
    },
});

export {
    Editor,
    Node,
    StarterKit,
    Markdown,
    CodeBlockLowlight,
    lowlight,
    LinkWithInputRule as Link,
    MarkdownTable,
    MarkdownTableRow,
    MarkdownTableCell,
    MarkdownTableHeader,
    MarkdownTaskList,
    MarkdownTaskItem,
    History,
};
