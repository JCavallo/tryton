/*
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to
deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/

(function () {
    'use strict';

    var tag_whitelist = {
        B: true,
        BODY: true,
        BR: true,
        DIV: true,
        FONT: true,
        I: true,
        U: true,
    };

    var attribute_whitelist = {
        align: true,
        color: true,
        face: true,
        size: true,
    };

    // The attributes stay the stored format (read back by the clients and
    // the reports) but they are also applied as inline style so that they
    // are not overridden by the stylesheets. Return null for values that
    // are not safe to use inside a style attribute.
    var font_sizes = {
        '1': 'x-small',
        '2': 'small',
        '3': 'medium',
        '4': 'large',
        '5': 'x-large',
        '6': 'xx-large',
        '7': 'xxx-large',
    };
    var attribute_styles = {
        align: function(value) {
            value = value.trim().toLowerCase();
            if (['left', 'right', 'center', 'justify'].includes(value)) {
                return 'text-align: ' + value;
            }
            return null;
        },
        color: function(value) {
            value = value.trim();
            if (/^(#[0-9a-f]{3,8}|[a-z]+)$/i.test(value)) {
                return 'color: ' + value;
            }
            return null;
        },
        face: function(value) {
            value = value.trim();
            if (/^[\w\s,'"-]+$/.test(value)) {
                return 'font-family: ' + value;
            }
            return null;
        },
        size: function(value) {
            value = font_sizes[value.trim()];
            if (value) {
                return 'font-size: ' + value;
            }
            return null;
        },
    };

    Sao.HtmlSanitizer = {};
    Sao.HtmlSanitizer.sanitize = function(input) {
        input = input.trim();
        // to save performance and not create iframe
        if (input == "") return "";

        // firefox "bogus node" workaround
        if (input == "<br>") return "";

        var iframe = document.createElement('iframe');
        if (iframe.sandbox === undefined) {
            // Browser does not support sandboxed iframes
            Sao.Logger.warn("Your browser do not support sandboxed iframes," +
                " unable to sanitize HTML.");
            return input;
        }
        iframe.sandbox = 'allow-same-origin';
        iframe.style.display = 'none';
        // necessary so the iframe contains a document
        document.body.appendChild(iframe);
        var iframedoc = (iframe.contentDocument ||
            iframe.contentWindow.document);
        // null in IE
        if (iframedoc.body == null) {
            iframedoc.write("<body></body>");
        }
        iframedoc.body.innerHTML = input;

        function make_sanitized_copy(node) {
            var new_node;
            if (node.nodeType == Node.TEXT_NODE) {
                new_node = node.cloneNode(true);
            } else if (node.nodeType == Node.ELEMENT_NODE &&
                    tag_whitelist[node.tagName]) {
                //remove useless empty tags
                if ((node.tagName != "BR") && node.innerHTML.trim() == "") {
                    return document.createDocumentFragment();
                }

                new_node = iframedoc.createElement(node.tagName);

                var styles = [];
                for (var i = 0; i < node.attributes.length; i++) {
                    var attr = node.attributes[i];
                    if (attribute_whitelist[attr.name]) {
                        new_node.setAttribute(attr.name, attr.value);
                        var style = attribute_styles[attr.name](attr.value);
                        if (style) {
                            styles.push(style);
                        }
                    }
                }
                if (styles.length) {
                    new_node.setAttribute("style", styles.join('; ') + ';');
                }
                for (i = 0; i < node.childNodes.length; i++) {
                    var sub_copy = make_sanitized_copy(node.childNodes[i]);
                    new_node.appendChild(sub_copy, false);
                }
            } else {
                new_node = document.createDocumentFragment();
                if (node.tagName != 'SCRIPT') {
                    new_node.textContent = node.textContent;
                }
            }
            return new_node;
        }

        var result_element = make_sanitized_copy(iframedoc.body);
        document.body.removeChild(iframe);
        // replace is just for cleaner code
        return result_element.innerHTML
            .replace(/<br[^>]*>(\S)/g, "<br>\n$1")
            .replace(/div><div/g, "div>\n<div");
    };
})();
