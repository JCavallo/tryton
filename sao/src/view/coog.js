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

    Object.assign(Sao.View.FormXMLViewParser.WIDGETS, {
        'json': Sao.View.Form.JSON,
    });

}());
