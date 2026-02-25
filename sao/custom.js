(function() {
    Sao.config.mount_point = '/sao';

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
