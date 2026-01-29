(function() {
    'use strict';

    Sao.View.Form.JSON = Sao.class_(Sao.View.Form.Widget, {
        class_: 'form-json form-text',
        expand: true,
        init: function(view, attributes) {
            Sao.View.Form.JSON._super.init.call(this, view, attributes);
            this.el = jQuery('<div/>', {
                'class': this.class_,
            });
            this.group = jQuery('<div/>', {
                'class': 'input-group',
            }).appendTo(this.el);
            this.input = this.labelled = jQuery('<textarea/>', {
                'class': 'form-control input-sm mousetrap',
                'name': attributes.name,
            }).appendTo(this.group);
        },
        set_readonly: function(readonly) {
            Sao.View.Form.JSON._super.set_readonly.call(this, readonly);
            this.input.prop('readonly', readonly);
        },
        display: function() {
            Sao.View.Form.JSON._super.display.call(this);
            let record = this.record;
            if (record) {
                let value = record.field_get_client(this.field_name);
                value = JSON.stringify(value, null, 2);
                if (this.attributes.yexpand) {
                    this.input.css('height', value.split('\n').length * 2.5 + 2 + "ex");
                }
                this.input.val(value);
            } else {
                this.input.val('');
            }
            return jQuery.when();
        },
    });

    Sao.View.Form.Billboard = Sao.class_(Sao.View.Form.Widget, {
        class_: 'form-billboard',
        init: function(view, attributes) {
            Sao.View.Form.Billboard._super.init.call(this, view, attributes);
            this.el = jQuery('<div/>', {
                'class': this.class_,
            });
            this.el.uniqueId();
            this._x_sao = {};
        },
        display: function() {
            let prm = Sao.View.Form.Billboard._super.display.call(this);
            if (!this.field || !this.record) {
                return prm;
            }

            let value = this.field.get_client(this.record);
            if (!value.data) {
                return prm;
            }
            this._x_sao = structuredClone(value['x-sao']);
            if (['pie', 'donut'].includes(value.data.type)) {
                this._remap_ids();
            }
            Object.assign(value, {
                bindto: `#${this.el.attr('id')}`,
            });
            if (value.data && Object.keys(value.data).length != 0) {
                value.data.onclick = this.action.bind(this);
            }
            let bb_node = document.getElementById(this.el.attr('id'));
            if (bb_node && Object.keys(value).length != 0) {
                bb.generate(value);
            }
            return prm;
        },
        action: function(data, element) {
            if (this._x_sao && this._x_sao.action) {
                let ids = this._x_sao.ids[data.id][data.index];
                let ctx = Object.assign({}, this.view.screen.local_context, this._x_sao.context || {});
                ctx.data_id = data.id;
                delete ctx.active_ids;
                delete ctx.active_id;
                Sao.Action.execute(this._x_sao.action, {
                    id: ((ids && ids.length > 0) ? ids[0] : null),
                    ids: ids,
                }, ctx, false);
            }
        },
        _remap_ids: function() {
            for (let [idx, value] of Object.values(this._x_sao.ids).entries()) {
                for (let i = 0; i < idx; i++) {
                    value.splice(0, 0, undefined);
                }
            }
        },
    });

    Object.assign(Sao.View.FormXMLViewParser.WIDGETS, {
        'json': Sao.View.Form.JSON,
        'billboard': Sao.View.Form.Billboard,
    });

}());
