module.exports = function(grunt) {

  var _ = grunt.util._;
  var locales = ["bg", "ca", "cs", "de", "es", "es_419", "fr", "fa", "hu",
      "it", "lo", "lt", "nl", "pl", "pt", "ru", "sl", "zh_CN"];
  var jsfiles = [
      'src/sao.js',
      'src/rpc.js',
      'src/pyson.js',
      'src/session.js',
      'src/common.js',
      'src/model.js',
      'src/tab.js',
      'src/screen.js',
      'src/view.js',
      'src/view/form.js',
      'src/view/tree.js',
      'src/view/graph.js',
      'src/view/calendar.js',
      'src/view/list_form.js',
      'src/action.js',
      'src/window.js',
      'src/wizard.js',
      'src/board.js',
      'src/bus.js',
      'src/chat.js',
      'src/notification.js',
      'src/user_menu.js',
      'src/plugins.js',
      'src/html_sanitizer.js',
      'src/view/coog.js',
  ];
  var less_paths = [
      'src',
      'node_modules',
      'node_modules/bootstrap',
      'node_modules/bootstrap/less',
      'node_modules/bootstrap-rtl-ondemand/less',
      'src/theme/coog',
  ];

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    shell: {
        options: {
            failOnError: true
        },
        tiptap: {
            command: 'node_modules/.bin/esbuild src/tiptap-entry.js' +
                ' --bundle --format=iife --global-name=Tiptap' +
                ' --outfile=dist/tiptap-bundle.js'
        },
        msgmerge: {
            command: _.map(locales, function(locale) {
                var po = "locale/" + locale + ".po";
                return (
                    "msgmerge " +
                    "-U " + po + " " +
                    "--no-location " +
                    "locale/messages.pot;");
            }).join("")
        },
        xgettext: {
            command: (
                "xgettext " +
                "--language=JavaScript --from-code=UTF-8 " +
                "--omit-header --no-location " +
                "-o locale/messages.pot " +
                jsfiles.join(" ") + " custom.js")
        }
    },
    po2json: {
        options: {
            format: 'raw'
        },
        all: {
            src: ['locale/*.po'],
            dest: 'locale/'
        }
    },
    concat: {
        dist: {
            src: jsfiles,
            dest: 'dist/<%= pkg.name %>.js'
        }
    },
    less: {
        'default': {
            options: {
                paths: less_paths,
            },
            files: {
                'dist/<%= pkg.name %>.css': 'src/sao.less'
            }
        }
    },
    watch: {
        scripts: {
            files: ['src/**/*.js'],
            tasks: ['concat']
        },
        styles: {
            files: [
                'src/*.less',
                'src/theme/coog/*.less',
                'src/theme/coog/elements/*.less'
            ],
            tasks: 'less'
        },
        translations: {
            files: ['locale/*.po'],
            tasks: 'po2json'
        }
    },
    qunit: {
        options: {
            timeout: 300000,
            puppeteer: {
                headless: true,
                args: [
                    '--no-sandbox',
                ],
                env: {
                    TZ: 'UTC',
                },
            },
        },
        all: ['tests/*.html']
    }
  });

  grunt.loadNpmTasks('grunt-contrib-concat');
  grunt.loadNpmTasks('grunt-contrib-less');
  grunt.loadNpmTasks('grunt-po2json');
  grunt.loadNpmTasks('grunt-shell');

  grunt.registerTask('qunit_junit', 'Write JUnit reports of qunit tests',
    function() {
      var dest = '_build/test-reports';
      var suite = null;
      var escape = function(value) {
        return String(value)
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;');
      };
      var seconds = function(runtime) {
        return ((runtime || 0) / 1000).toFixed(3);
      };
      grunt.event.on('qunit.spawn', function(url) {
        suite = {
          name: url.replace(/^.*\//, '').replace(/\.html?$/, ''),
          testcases: [],
          failures: 0,
          skipped: 0,
        };
      });
      grunt.event.on('qunit.on.testEnd', function(test) {
        if (!suite) {
          return;
        }
        var classname = (test.fullName || []).slice(0, -1).join(' > ') ||
          test.moduleName || suite.name;
        var xml = '    <testcase classname="' + escape(classname) +
          '" name="' + escape(test.name) +
          '" time="' + seconds(test.runtime) + '"';
        if (test.status == 'failed') {
          suite.failures += 1;
          var errors = (test.errors || []).map(function(error) {
            var lines = [error.message];
            if ('expected' in error) {
              lines.push('Actual: ' + JSON.stringify(error.actual));
              lines.push('Expected: ' + JSON.stringify(error.expected));
            }
            lines.push(error.stack);
            return lines.filter(Boolean).join('\n');
          });
          xml += '>\n      <failure message="' +
            escape((test.errors || [{}])[0].message || 'failed') + '">' +
            escape(errors.join('\n\n')) + '</failure>\n    </testcase>';
        } else if (test.status == 'skipped' || test.status == 'todo') {
          suite.skipped += 1;
          xml += '>\n      <skipped/>\n    </testcase>';
        } else {
          xml += '/>';
        }
        suite.testcases.push(xml);
      });
      // Written on runEnd as the qunit task aborts on failure
      grunt.event.on('qunit.on.runEnd', function(run) {
        if (!suite) {
          return;
        }
        var xml = '<?xml version="1.0" encoding="UTF-8"?>\n' +
          '<testsuites>\n' +
          '  <testsuite name="' + escape(suite.name) +
          '" tests="' + suite.testcases.length +
          '" failures="' + suite.failures +
          '" errors="0" skipped="' + suite.skipped +
          '" time="' + seconds(run.runtime) + '">\n' +
          suite.testcases.join('\n') + '\n' +
          '  </testsuite>\n' +
          '</testsuites>\n';
        grunt.file.write(dest + '/TEST-' + suite.name + '.xml', xml);
        suite = null;
      });
      grunt.log.ok('XML reports will be written to ' + dest);
    });

  grunt.registerTask('default', 'Build for production.', function() {
    grunt.task.run(['concat', 'less', 'po2json', 'shell:tiptap']);
    });
  grunt.registerTask('watch', 'Watch development', function() {
    grunt.loadNpmTasks('grunt-contrib-watch');
    grunt.task.run(['watch']);
    });
  grunt.registerTask('msgmerge', 'Update locale messages.', function() {
    grunt.task.run(['shell:msgmerge']);
    });
  grunt.registerTask('xgettext', ' Extracts translatable messages', function() {
    grunt.task.run(['shell:xgettext']);
  });
  grunt.registerTask('test', 'Run tests', function() {
    grunt.loadNpmTasks('grunt-contrib-qunit');
    grunt.task.run(['concat', 'less', 'qunit_junit', 'qunit']);
    });

};
