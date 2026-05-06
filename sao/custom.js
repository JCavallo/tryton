(function() {
    Sao.config.mount_point = '/sao';

    var _md_svg = function(inner) {
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"' +
            ' width="16" height="16" fill="none" stroke="currentColor"' +
            ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            inner + '</svg>';
    };
    var MD_ICONS = {
        undo: _md_svg('<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>'),
        redo: _md_svg('<path d="m15 14 5-5-5-5"/><path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13"/>'),
        bold: _md_svg('<path d="M14 12a4 4 0 0 0 0-8H6v8"/><path d="M15 20a4 4 0 0 0 0-8H6v8z"/>'),
        italic: _md_svg('<line x1="19" x2="10" y1="4" y2="4"/><line x1="14" x2="5" y1="20" y2="20"/><line x1="15" x2="9" y1="4" y2="20"/>'),
        strike: _md_svg('<path d="M16 4H9a3 3 0 0 0-2.83 4"/><path d="M14 12a4 4 0 0 1 0 8H6"/><line x1="4" x2="20" y1="12" y2="12"/>'),
        underline: _md_svg('<path d="M6 4v6a6 6 0 0 0 12 0V4"/><line x1="4" x2="20" y1="20" y2="20"/>'),
        code: _md_svg('<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>'),
        h1: _md_svg('<path d="M4 12h8"/><path d="M4 18V6"/><path d="M12 18V6"/><path d="m17 12 3-2v8"/>'),
        h2: _md_svg('<path d="M4 12h8"/><path d="M4 18V6"/><path d="M12 18V6"/><path d="M21 18h-4c0-4 4-3 4-6 0-1.5-2-2.5-4-1"/>'),
        h3: _md_svg('<path d="M4 12h8"/><path d="M4 18V6"/><path d="M12 18V6"/><path d="M17.5 10.5c1.7-1 3.5 0 3.5 1.5a2 2 0 0 1-2 2"/><path d="M17 17.5c2 1.5 4 .3 4-1.5a2 2 0 0 0-2-2"/>'),
        bulletList: _md_svg('<line x1="9" x2="20" y1="6" y2="6"/><line x1="9" x2="20" y1="12" y2="12"/><line x1="9" x2="20" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/>'),
        orderedList: _md_svg('<line x1="10" x2="21" y1="6" y2="6"/><line x1="10" x2="21" y1="12" y2="12"/><line x1="10" x2="21" y1="18" y2="18"/><path d="M4 6h1v4"/><path d="M4 10h2"/><path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/>'),
        taskList: _md_svg('<path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/><line x1="13" x2="21" y1="8" y2="8"/><line x1="13" x2="21" y1="16" y2="16"/>'),
        blockquote: _md_svg('<path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"/><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 0 1 1 1z"/>'),
        codeBlock: _md_svg('<rect width="20" height="20" x="2" y="2" rx="2" ry="2"/><path d="m10 10-2 2 2 2"/><path d="m14 14 2-2-2-2"/>'),
        table: _md_svg('<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><line x1="3" x2="21" y1="9" y2="9"/><line x1="3" x2="21" y1="15" y2="15"/><line x1="9" x2="9" y1="3" y2="21"/><line x1="15" x2="15" y1="3" y2="21"/>'),
        hr: _md_svg('<line x1="5" x2="19" y1="12" y2="12"/>'),
        link: _md_svg('<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'),
        source: _md_svg('<path d="M9 9L4 12l5 3"/><path d="M15 9l5 3-5 3"/><line x1="12" x2="12" y1="6" y2="18"/>'),
        image: _md_svg('<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>'),
    };

    var MD_MAX_IMAGE_BYTES = 5 * 1024 * 1024;
    var MD_ALLOWED_IMAGE_MIMES = [
        'image/png', 'image/jpeg', 'image/gif', 'image/webp'];
    var MD_RES_RE = /^md-res:([0-9a-f]{32})$/;

    var _md_bytes_to_data_url = function(bytes, mime) {
        if (!bytes) { return null; }
        if (typeof bytes === 'string') {
            return 'data:' + (mime || 'image/png') + ';base64,' + bytes;
        }
        var binary = '';
        var chunk = 0x8000;
        for (var i = 0; i < bytes.length; i += chunk) {
            binary += String.fromCharCode.apply(null,
                bytes.subarray(i, Math.min(i + chunk, bytes.length)));
        }
        return 'data:' + (mime || 'image/png') + ';base64,' + btoa(binary);
    };

    var _md_sniff_mime = function(bytes) {
        if (!(bytes instanceof Uint8Array)) { return null; }
        if (bytes.length >= 8 && bytes[0] === 0x89 && bytes[1] === 0x50 &&
            bytes[2] === 0x4e && bytes[3] === 0x47) {
            return 'image/png';
        }
        if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 &&
            bytes[2] === 0xff) {
            return 'image/jpeg';
        }
        if (bytes.length >= 6 && bytes[0] === 0x47 && bytes[1] === 0x49 &&
            bytes[2] === 0x46 && bytes[3] === 0x38) {
            return 'image/gif';
        }
        if (bytes.length >= 12 &&
            bytes[0] === 0x52 && bytes[1] === 0x49 &&
            bytes[2] === 0x46 && bytes[3] === 0x46 &&
            bytes[8] === 0x57 && bytes[9] === 0x45 &&
            bytes[10] === 0x42 && bytes[11] === 0x50) {
            return 'image/webp';
        }
        return null;
    };

    var _md_new_uuid = function() {
        var bytes = new Uint8Array(16);
        window.crypto.getRandomValues(bytes);
        var hex = '';
        for (var i = 0; i < bytes.length; i++) {
            hex += ('0' + bytes[i].toString(16)).slice(-2);
        }
        return hex;
    };

    var MD_IMAGE_NODE = Tiptap.Node.create({
        name: 'image',
        group: 'inline',
        inline: true,
        atom: true,
        selectable: true,
        draggable: true,
        addOptions: function() {
            return {widget: null};
        },
        addAttributes: function() {
            return {
                src: {default: null},
                alt: {default: null},
                title: {default: null},
            };
        },
        parseHTML: function() {
            return [{tag: 'img[src]'}];
        },
        renderHTML: function(props) {
            var attrs = props.HTMLAttributes || {};
            var widget = this.options.widget;
            var src = attrs.src || '';
            var display_src = src;
            var match = MD_RES_RE.exec(src);
            if (match && widget && widget._image_cache) {
                var cached = widget._image_cache.get(match[1]);
                display_src = cached || '';
            }
            var out = jQuery.extend({}, attrs, {src: display_src});
            // Keep data-md-res so _refresh_image_nodes() can patch src in-place
            // once the async data URL resolves, without re-rendering the editor.
            if (match) {
                out['data-md-res'] = match[1];
            }
            return ['img', out];
        },
        markdownTokenName: 'image',
        parseMarkdown: function(token, helpers) {
            return helpers.createNode('image', {
                src: token.href,
                alt: token.text,
                title: token.title || null,
            });
        },
        renderMarkdown: function(node) {
            var attrs = node.attrs || {};
            var alt = attrs.alt || '';
            var src = attrs.src || '';
            var title = attrs.title ? ' "' + attrs.title + '"' : '';
            return '![' + alt + '](' + src + title + ')';
        },
    });

    Sao.View.Form.Markdown = Sao.class_(Sao.View.Form.Widget, {
        class_: 'form-markdown',
        expand: true,
        init: function(view, attributes) {
            Sao.View.Form.Markdown._super.init.call(this, view, attributes);
            this._show_toolbar = parseInt(attributes.toolbar || '1', 10) !== 0;
            this._source_mode = false;
            this._image_cache = new Map();
            this._file_input = jQuery('<input/>', {
                'type': 'file',
                'accept': MD_ALLOWED_IMAGE_MIMES.join(','),
            }).css('display', 'none').on('change', (ev) => {
                var pos = this._pending_insert_pos;
                this._pending_insert_pos = undefined;
                var files = ev.target.files;
                if (files && files.length) {
                    for (var i = 0; i < files.length; i++) {
                        this._insert_image_from_file(files[i], pos);
                        pos = null;
                    }
                }
                ev.target.value = '';
            });
            this.el = jQuery('<div/>', {
                'class': this.class_ + ' panel panel-default',
            });
            this.el.append(this._file_input);
            this.prev_record = undefined;
            this._toolbar_heading = jQuery('<div/>', {
                'class': 'panel-heading',
            }).appendTo(this.el);
            this.toolbar = this._build_toolbar().appendTo(
                this._toolbar_heading);
            this._table_toolbar = this._build_table_toolbar().appendTo(
                this._toolbar_heading);
            var body = jQuery('<div/>', {
                'class': 'panel-body',
            }).appendTo(this.el);
            this._mount = jQuery('<div/>', {
                'class': 'markdown-editor mousetrap',
            }).appendTo(body);
            this._source_textarea = jQuery('<textarea/>', {
                'class': 'markdown-source',
            }).appendTo(body).hide()
                .on('input', () => {
                    this.send_modified();
                    this._resize_source_textarea();
                })
                .on('blur', () => {
                    Sao.View.Form.Markdown._super.focus_out.call(this);
                });
            this._editor = new Tiptap.Editor({
                element: this._mount[0],
                extensions: [
                    Tiptap.StarterKit.configure({codeBlock: false, link: false}),
                    Tiptap.Markdown,
                    Tiptap.CodeBlockLowlight.configure({lowlight: Tiptap.lowlight}),
                    Tiptap.Link.configure({openOnClick: false}),
                    Tiptap.MarkdownTable.configure({resizable: false}),
                    Tiptap.MarkdownTableRow,
                    Tiptap.MarkdownTableCell,
                    Tiptap.MarkdownTableHeader,
                    Tiptap.MarkdownTaskList,
                    Tiptap.MarkdownTaskItem.configure({nested: true}),
                    MD_IMAGE_NODE.configure({widget: this}),
                ],
                content: '',
                marked: {
                    gfm: true,
                    breaks: false,
                    pedantic: false
                },
                onUpdate: () => {
                    this.send_modified();
                    this._update_toolbar_state();
                },
                onSelectionUpdate: () => {
                    this._update_toolbar_state();
                },
                onBlur: () => {
                    Sao.View.Form.Markdown._super.focus_out.call(this);
                },
                editorProps: {
                    handleDrop: (view, event, slice, moved) => {
                        if (moved) { return false; }
                        var files = event.dataTransfer &&
                            event.dataTransfer.files;
                        if (!files || !files.length) { return false; }
                        var image_files = [];
                        for (var i = 0; i < files.length; i++) {
                            if (files[i].type &&
                                    files[i].type.indexOf('image/') === 0) {
                                image_files.push(files[i]);
                            }
                        }
                        if (!image_files.length) { return false; }
                        event.preventDefault();
                        var coords = view.posAtCoords({
                            left: event.clientX, top: event.clientY});
                        var pos = coords ? coords.pos : null;
                        for (var f = 0; f < image_files.length; f++) {
                            this._insert_image_from_file(image_files[f], pos);
                            pos = null;
                        }
                        return true;
                    },
                    handlePaste: (view, event) => {
                        var items = event.clipboardData &&
                            event.clipboardData.items;
                        if (!items) { return false; }
                        var image_files = [];
                        for (var i = 0; i < items.length; i++) {
                            if (items[i].kind !== 'file') { continue; }
                            var f = items[i].getAsFile();
                            if (f && f.type &&
                                    f.type.indexOf('image/') === 0) {
                                image_files.push(f);
                            }
                        }
                        if (!image_files.length) { return false; }
                        event.preventDefault();
                        for (var k = 0; k < image_files.length; k++) {
                            this._insert_image_from_file(image_files[k]);
                        }
                        return true;
                    },
                    handleKeyDown: (view, event) => {
                        if (event.ctrlKey && event.shiftKey && event.key === 'V') {
                            event.preventDefault();
                            if (navigator.clipboard && navigator.clipboard.readText) {
                                navigator.clipboard.readText().then(text => {
                                    if (text) {
                                        const { state, dispatch } = view;
                                        dispatch(state.tr.insertText(text));
                                    }
                                }).catch(() => {});
                            }
                            return true;
                        }
                        return false;
                    },
                },
            });
        },
        _build_toolbar: function() {
            var toolbar = jQuery('<div class="md-toolbar"/>');
            this._toolbar_btns = {};

            var add_btn = (key, icon, label, command) => {
                var btn = jQuery('<button/>', {
                    'class': 'md-btn',
                    'type': 'button',
                    'title': label,
                }).html(icon).appendTo(toolbar);
                btn.on('mousedown', (ev) => ev.preventDefault());
                btn.click(() => command(this._editor));
                this._toolbar_btns[key] = btn;
            };

            var add_sep = () => jQuery('<span class="md-sep"/>').appendTo(toolbar);

            add_btn('undo', MD_ICONS.undo, Sao.i18n.gettext("Undo"),
                (e) => e.chain().focus().undo().run());
            add_btn('redo', MD_ICONS.redo, Sao.i18n.gettext("Redo"),
                (e) => e.chain().focus().redo().run());
            add_sep();
            add_btn('bold', MD_ICONS.bold, Sao.i18n.gettext("Bold"),
                (e) => e.chain().focus().toggleBold().run());
            add_btn('italic', MD_ICONS.italic, Sao.i18n.gettext("Italic"),
                (e) => e.chain().focus().toggleItalic().run());
            add_btn('strike', MD_ICONS.strike, Sao.i18n.gettext("Strikethrough"),
                (e) => e.chain().focus().toggleStrike().run());
            add_btn('underline', MD_ICONS.underline, Sao.i18n.gettext("Underline"),
                (e) => e.chain().focus().toggleUnderline().run());
            add_btn('code', MD_ICONS.code, Sao.i18n.gettext("Inline code"),
                (e) => e.chain().focus().toggleCode().run());
            add_sep();
            add_btn('h1', MD_ICONS.h1, Sao.i18n.gettext("Heading 1"),
                (e) => e.chain().focus().toggleHeading({level: 1}).run());
            add_btn('h2', MD_ICONS.h2, Sao.i18n.gettext("Heading 2"),
                (e) => e.chain().focus().toggleHeading({level: 2}).run());
            add_btn('h3', MD_ICONS.h3, Sao.i18n.gettext("Heading 3"),
                (e) => e.chain().focus().toggleHeading({level: 3}).run());
            add_sep();
            add_btn('bulletList', MD_ICONS.bulletList, Sao.i18n.gettext("Bullet list"),
                (e) => e.chain().focus().toggleBulletList().run());
            add_btn('orderedList', MD_ICONS.orderedList, Sao.i18n.gettext("Ordered list"),
                (e) => e.chain().focus().toggleOrderedList().run());
            add_btn('taskList', MD_ICONS.taskList, Sao.i18n.gettext("Task list"),
                (e) => e.chain().focus().toggleTaskList().run());
            add_sep();
            add_btn('blockquote', MD_ICONS.blockquote, Sao.i18n.gettext("Blockquote"),
                (e) => e.chain().focus().toggleBlockquote().run());
            add_btn('codeBlock', MD_ICONS.codeBlock, Sao.i18n.gettext("Code block"),
                (e) => e.chain().focus().toggleCodeBlock().run());
            add_sep();
            add_btn('table', MD_ICONS.table, Sao.i18n.gettext("Insert table"),
                (e) => e.chain().focus().insertTable(
                    {rows: 3, cols: 3, withHeaderRow: true}).run());
            add_btn('hr', MD_ICONS.hr, Sao.i18n.gettext("Horizontal rule"),
                (e) => e.chain().focus().setHorizontalRule().run());
            add_btn('image', MD_ICONS.image, Sao.i18n.gettext("Insert image"),
                () => {
                    try {
                        this._pending_insert_pos =
                            this._editor.state.selection.from;
                    } catch (e) {
                        this._pending_insert_pos = undefined;
                    }
                    this._file_input.trigger('click');
                });
            add_btn('link', MD_ICONS.link, Sao.i18n.gettext("Link"),
                (e) => {
                    if (e.isActive('link')) {
                        e.chain().focus().unsetLink().run();
                        return;
                    }
                    var current = e.getAttributes('link').href || '';
                    var url = window.prompt(
                        Sao.i18n.gettext("Link URL"), current);
                    if (url === null) { return; }
                    if (url === '') {
                        e.chain().focus().unsetLink().run();
                    } else {
                        e.chain().focus().setLink({href: url}).run();
                    }
                });
            add_sep();
            add_btn('source', MD_ICONS.source, Sao.i18n.gettext("Toggle source"),
                () => this._toggle_source());

            return toolbar;
        },
        _build_table_toolbar: function() {
            var toolbar = jQuery('<div class="md-table-toolbar"/>');
            this._table_btns = {};

            var add_btn = (key, label, title, command) => {
                var btn = jQuery('<button/>', {
                    'class': 'md-btn md-table-btn',
                    'type': 'button',
                    'title': title,
                }).text(label).appendTo(toolbar);
                btn.on('mousedown', (ev) => ev.preventDefault());
                btn.click(() => command(this._editor));
                this._table_btns[key] = btn;
            };

            var add_sep = () => jQuery('<span class="md-sep"/>').appendTo(toolbar);

            add_btn('addRowBefore', '+row\u2191', Sao.i18n.gettext("Add row above"),
                (e) => e.chain().focus().addRowBefore().run());
            add_btn('addRowAfter', '+row\u2193', Sao.i18n.gettext("Add row below"),
                (e) => e.chain().focus().addRowAfter().run());
            add_btn('deleteRow', '\u2212row', Sao.i18n.gettext("Delete row"),
                (e) => e.chain().focus().deleteRow().run());
            add_sep();
            add_btn('addColumnBefore', '+col\u2190', Sao.i18n.gettext("Add column before"),
                (e) => e.chain().focus().addColumnBefore().run());
            add_btn('addColumnAfter', '+col\u2192', Sao.i18n.gettext("Add column after"),
                (e) => e.chain().focus().addColumnAfter().run());
            add_btn('deleteColumn', '\u2212col', Sao.i18n.gettext("Delete column"),
                (e) => e.chain().focus().deleteColumn().run());
            add_sep();
            add_btn('deleteTable', '\u00d7table', Sao.i18n.gettext("Delete table"),
                (e) => e.chain().focus().deleteTable().run());

            return toolbar;
        },
        _resize_source_textarea: function() {
            var el = this._source_textarea[0];
            var scrollY = window.scrollY;
            el.style.height = 'auto';
            el.style.height = el.scrollHeight + 'px';
            window.scrollTo(window.scrollX, scrollY);
        },
        _toggle_source: function() {
            this._source_mode = !this._source_mode;
            if (this._source_mode) {
                var editorHeight = this._mount[0].offsetHeight;
                this._source_textarea
                    .val(this._editor.getMarkdown())
                    .css('height', editorHeight + 'px');
                this._mount.hide();
                this._source_textarea.show();
                this._source_textarea[0].focus({preventScroll: true});
                this._table_toolbar.removeClass('is-visible');
                this.toolbar.find('.md-btn').not(this._toolbar_btns.source)
                    .prop('disabled', true);
                this._toolbar_btns.source.addClass('is-active');
            } else {
                var md = this._source_textarea.val();
                this._source_textarea.hide().css('height', '');
                this._mount.show();
                this._editor.commands.setContent(
                    md, {contentType: 'markdown', emitUpdate: false});
                this.send_modified();
                this._toolbar_btns.source.removeClass('is-active');
                this.toolbar.find('.md-btn').prop('disabled', false);
                this._update_toolbar_state();
                this._editor.commands.focus(null, {scrollIntoView: false});
            }
        },
        _update_toolbar_state: function() {
            if (!this._editor || !this._toolbar_btns) {
                return;
            }
            if (this._source_mode) {
                this._table_toolbar.removeClass('is-visible');
                return;
            }
            var e = this._editor;
            var states = {
                bold: e.isActive('bold'),
                italic: e.isActive('italic'),
                strike: e.isActive('strike'),
                underline: e.isActive('underline'),
                code: e.isActive('code'),
                h1: e.isActive('heading', {level: 1}),
                h2: e.isActive('heading', {level: 2}),
                h3: e.isActive('heading', {level: 3}),
                bulletList: e.isActive('bulletList'),
                orderedList: e.isActive('orderedList'),
                taskList: e.isActive('taskList'),
                blockquote: e.isActive('blockquote'),
                codeBlock: e.isActive('codeBlock'),
                link: e.isActive('link'),
            };
            for (var key in states) {
                if (this._toolbar_btns[key]) {
                    this._toolbar_btns[key].toggleClass('is-active', states[key]);
                }
            }
            if (this._toolbar_btns.undo) {
                this._toolbar_btns.undo.prop('disabled', !e.can().undo());
            }
            if (this._toolbar_btns.redo) {
                this._toolbar_btns.redo.prop('disabled', !e.can().redo());
            }
            this._table_toolbar.toggleClass('is-visible', e.isActive('table'));
        },
        display: function() {
            var prm = Sao.View.Form.Markdown._super.display.call(this);
            var value = '';
            var record = this.record;
            if (record) {
                value = record.field_get_client(this.field_name) || '';
            }
            var record_changed = (this.record !== this.prev_record);
            if (record_changed) {
                this._image_cache.clear();
            }
            this._editor.commands.setContent(
                value, {contentType: 'markdown', emitUpdate: false});
            if (this._source_mode) {
                this._source_textarea.val(value);
            }
            if (record_changed) {
                this.prev_record = this.record;
                // tiptap-pm History has no clearHistory() API; unregister+re-register
                // is the only way to reset undo state when switching records.
                this._editor.unregisterPlugin('history');
                this._editor.registerPlugin(Tiptap.History({}));
            }
            // Load images asynchronously; _cache_resource calls
            // _refresh_image_nodes() per image as data URLs become available.
            this._sync_image_cache();
            return prm;
        },
        _get_markdown_resources_group: function() {
            if (!this.record) { return null; }
            try {
                return this.record.field_get_client('markdown_resources');
            } catch (e) {
                return null;
            }
        },
        _live_resources: function(group) {
            // Pending removals stay in the group array until the parent record
            // is saved; filter them out so we don't try to load their data.
            var removed = group.record_removed || [];
            var deleted = group.record_deleted || [];
            var all = [];
            for (var i = 0; i < group.length; i++) {
                var r = group[i];
                if (removed.indexOf(r) >= 0 || deleted.indexOf(r) >= 0) {
                    continue;
                }
                all.push(r);
            }
            return all;
        },
        _sync_image_cache: function() {
            var group = this._get_markdown_resources_group();
            if (!group) { return jQuery.when(); }
            return jQuery.when(this._ensure_resource_fields(group)).then(
                () => {
                    var all = this._live_resources(group);
                    if (!all.length) { return; }
                    return this._load_resources_meta(group, all).then(() => {
                        var matches = all.filter((r) => {
                            try {
                                return r.field_get_client('field') ===
                                    this.field_name;
                            } catch (e) { return false; }
                        });
                        var promises = matches.map(
                            (r) => this._cache_resource(r));
                        return jQuery.when.apply(jQuery, promises);
                    });
                });
        },
        _load_resources_meta: function(group, resources) {
            // New (unsaved) records already have uuid/field set client-side.
            // For saved records, field_get_client() would trigger a lazy fetch
            // that may not resolve before we filter by field name, so we
            // batch-read and inject directly into _values/_loaded.
            var to_load = resources.filter(
                (r) => r.id >= 0 && !r.is_loaded('uuid'));
            if (!to_load.length) { return jQuery.when(); }
            var ids = to_load.map((r) => r.id);
            return jQuery.when(group.model.execute(
                'read', [ids, ['uuid', 'field']])).then((rows) => {
                    var by_id = {};
                    rows.forEach((row) => { by_id[row.id] = row; });
                    to_load.forEach((r) => {
                        var row = by_id[r.id];
                        if (!row) { return; }
                        r._values.uuid = row.uuid;
                        r._values.field = row.field;
                        r._loaded.uuid = true;
                        r._loaded.field = true;
                    });
                });
        },
        _cache_resource: function(resource) {
            var uuid;
            try {
                uuid = resource.field_get_client('uuid');
            } catch (e) { return jQuery.when(); }
            if (!uuid || this._image_cache.has(uuid)) {
                return jQuery.when();
            }
            var image_field = resource.model.fields.image;
            if (!image_field) { return jQuery.when(); }
            var data_prm = image_field.get_data(resource);
            return jQuery.when(data_prm).then((data) => {
                if (!data) { return; }
                var mime;
                if (data instanceof Uint8Array) {
                    mime = _md_sniff_mime(data);
                }
                this._image_cache.set(uuid,
                    _md_bytes_to_data_url(data, mime));
                this._refresh_image_nodes();
            });
        },
        _refresh_image_nodes: function() {
            if (!this._editor || !this._editor.view) { return; }
            var dom = this._editor.view.dom;
            jQuery(dom).find('img[data-md-res]').each((_, img) => {
                var uuid = img.getAttribute('data-md-res');
                var cached = this._image_cache.get(uuid);
                if (cached) {
                    img.src = cached;
                }
            });
        },
        _ensure_resource_fields: function(group) {
            var needed = ['field', 'uuid', 'image'];
            var missing = needed.filter(
                (n) => !group.model.fields[n]);
            if (!missing.length) { return jQuery.when(); }
            return jQuery.when(group.model.execute(
                'fields_get', [missing])).then((descs) => {
                    group.add_fields(descs);
                });
        },
        _insert_image_from_file: function(file, pos) {
            if (!this.record) { return; }
            if (MD_ALLOWED_IMAGE_MIMES.indexOf(file.type) === -1) {
                this._show_image_error(
                    Sao.i18n.gettext("Unsupported image type"));
                return;
            }
            if (file.size > MD_MAX_IMAGE_BYTES) {
                var mb = Math.floor(MD_MAX_IMAGE_BYTES / 1024 / 1024);
                this._show_image_error(
                    Sao.i18n.gettext("Image too large (max ") +
                    mb + ' MB)');
                return;
            }
            var reader = new FileReader();
            reader.onload = (ev) => {
                var bytes = new Uint8Array(ev.target.result);
                var uuid = _md_new_uuid();
                var group;
                try {
                    group = this.record.field_get_client(
                        'markdown_resources');
                } catch (e) {
                    this._show_image_error(Sao.i18n.gettext(
                        "Cannot insert image: record does not support" +
                        " markdown resources"));
                    return;
                }
                if (!group) {
                    this._show_image_error(Sao.i18n.gettext(
                        "Cannot insert image: markdown_resources field" +
                        " is not loaded in this view"));
                    return;
                }
                jQuery.when(this._ensure_resource_fields(group)).then(() => {
                    // Cache the data URL immediately so renderHTML can resolve
                    // the md-res: src before the record is saved.
                    this._image_cache.set(uuid,
                        _md_bytes_to_data_url(bytes, file.type));
                    var node = {
                        type: 'image',
                        attrs: {
                            src: 'md-res:' + uuid,
                            alt: file.name || '',
                        },
                    };
                    var chain = this._editor.chain().focus();
                    if (pos !== undefined && pos !== null) {
                        chain.insertContentAt(pos, node);
                    } else {
                        chain.insertContent(node);
                    }
                    chain.run();
                    // Commit the markdown text (with the md-res: token) to the
                    // field before creating the resource record so both stay in
                    // sync if the parent record is saved immediately.
                    this.set_value();
                    var new_record = group.new_(false);
                    new_record.model.fields.field.set_client(
                        new_record, this.field_name);
                    new_record.model.fields.uuid.set_client(
                        new_record, uuid);
                    new_record.model.fields.image.set_client(
                        new_record, bytes);
                    group.add(new_record, -1, true);
                });
            };
            reader.onerror = () => {
                this._show_image_error(
                    Sao.i18n.gettext("Could not read image file"));
            };
            reader.readAsArrayBuffer(file);
        },
        _show_image_error: function(message) {
            if (this._error_tip) {
                this._error_tip.remove();
            }
            var tip = jQuery('<div class="md-image-error"/>').text(message);
            this._error_tip = tip;
            var anchor = null;
            try {
                var view = this._editor.view;
                var sel = view.state.selection;
                var coords = view.coordsAtPos(sel.from);
                anchor = {left: coords.left, top: coords.bottom};
            } catch (e) { /* fall through */ }
            if (!anchor) {
                var rect = this._mount[0].getBoundingClientRect();
                anchor = {left: rect.left + 8, top: rect.top + 8};
            }
            tip.css({
                position: 'fixed',
                left: anchor.left + 'px',
                top: (anchor.top + 4) + 'px',
            }).appendTo('body');
            tip.on('click', () => tip.remove());
            setTimeout(() => {
                if (tip === this._error_tip) { this._error_tip = null; }
                tip.remove();
            }, 4000);
        },
        focus: function() {
            if (this._source_mode) {
                this._source_textarea[0].focus();
            } else {
                this._editor.commands.focus();
            }
        },
        get_value: function() {
            if (this._source_mode) {
                return this._source_textarea.val();
            }
            return this._editor.getMarkdown();
        },
        set_value: function() {
            this.field.set_client(this.record, this.get_value());
        },
        get modified() {
            if (this.record && this.field) {
                return this.field.get_client(this.record) != this.get_value();
            }
            return false;
        },
        set_readonly: function(readonly) {
            Sao.View.Form.Markdown._super.set_readonly.call(this, readonly);
            var record = this.record;
            var disabled = readonly || !record;
            this._editor.setEditable(!disabled);
            this._source_textarea.prop('readonly', disabled);
            this.toolbar.find('button').prop('disabled', disabled);
            this._table_toolbar.find('button').prop('disabled', disabled);
            if (disabled || !this._show_toolbar) {
                this._toolbar_heading.hide();
            } else {
                this._toolbar_heading.show();
                if (this._source_mode) {
                    this.toolbar.find('.md-btn').not(this._toolbar_btns.source)
                        .prop('disabled', true);
                }
            }
        },
    });
    Sao.View.FormXMLViewParser.WIDGETS['markdown'] =
        Sao.View.Form.Markdown;



    Sao.Tab.contextmenu = function(evt) {
        evt.preventDefault();
        evt.stopPropagation();

        let close_tabs = (mode) => {
            return () => {
                let tabs_to_close = [];
                let target_tab = jQuery(evt.currentTarget).closest('li').data('tab');
                let met_target = false;
                for (let tab of Sao.Tab.tabs) {
                    if (tab == target_tab) {
                        met_target = true;
                        continue;
                    }
                    if (met_target && (mode == 'left')) {
                        break;
                    }
                    if ((['left', 'others'].includes(mode)) || met_target) {
                        tabs_to_close.push(tab);
                    }
                }

                let prm = null;
                for (let tab of tabs_to_close) {
                    if (prm) {
                        prm = prm.then(() => tab._close_allowed());
                    } else {
                        prm = tab._close_allowed();
                    }
                }
                if (prm) {
                    prm.then(() => {
                        for (let tab of tabs_to_close) {
                            tab.close();
                        }
                    });
                }
            }
        }

        let actions = {
            close_others: close_tabs('others'),
            close_left: close_tabs('left'),
            close_right: close_tabs('right'),
            duplicate: () => {
                let current = Sao.Tab.tabs.get_current();
                Sao.Tab.create(current.attributes, true).then((t) => t.show());
            },
            in_new_tab: () => {
                window.open(window.location.href, '_blank').focus();
            },
        };

        let tab = Sao.Tab.tabs.get_current();
        let menu = Sao.common.PopupMenu.initialize(evt);
        for (const [action, name] of [
            ['close_others', Sao.i18n.gettext("Close all other tabs")],
            ['close_left', Sao.i18n.gettext("Close tabs to the left")],
            ['close_right', Sao.i18n.gettext("Close tabs to the right")],
            ['duplicate', Sao.i18n.gettext("Duplicate the tab")],
            ['in_new_tab', Sao.i18n.gettext("Open in a new browser tab")],
        ]) {
            let menuitem = jQuery('<li/>', {
                'role': 'presentation',
            }).append(jQuery('<a/>', {
                'role': 'menuitem',
                'href': '#',
                'tabindex': -1
            }).text(name).click(actions[action])
            ).appendTo(menu);

            if (((action == 'duplicate') || (action == 'in_new_tab')) &&
                (tab instanceof Sao.Tab.Wizard)) {
                menuitem.addClass("disabled");
                menuitem.children('a').css('pointer-events', 'none');
            }
        }
    };

    Sao.Tab.closed_tabs = [];
    Sao.Tab.undo_close = function() {
        if (Sao.Tab.closed_tabs.length == 0) {
            return;
        }
        let attributes = Sao.Tab.closed_tabs.pop();
        Sao.Tab.create(attributes, true);
    };

}());
