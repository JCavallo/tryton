#!/bin/bash

GDRIVE_FOLDER_ID=1yQaeqEMAaD6chcF4YMpmUZe9L3YoGa89

version() {
    local t
    # Old "t" variable before "automatic build" feature
    # t=$(git describe --tags --exact-match 2> /dev/null | grep "^coog-" | head -1)

    # Explaination of the "t" variable
    # Retrieve all tags attached to the current branch with a specific format:
    # git log --first-parent --pretty=%d
    # Retrieve all occurrences of "tag: <something> (ignoring commas and closed parentheses):
    # grep -o 'tag: [^,)]*'
    # We remove “tag:” from the result:
    # awk '{print $2}'
    # We ignore results containing “-rc”:
    # grep -v '-rc'
    # We limit the results to the format coog-2.14.2404 or coog-22.14.2404 or coog-2.14.2404.1 or coog-22.14.2404.1:
    # grep -Eo 'coog-[0-9]{1,2}.[0-9]{1,2}.[0-9]{4}(.[0-9]+)?$'
    # We select only the first result:
    # head -n 1
    t=$(git log --first-parent --pretty=%d | grep -o 'tag: [^,)]*' | awk '{print $2}' | grep -v '\-rc' | grep -Eo 'coog-[0-9]{1,2}.[0-9]{1,2}.[0-9]{4}(.[0-9]+)?$' | head -n 1)
    
    if [ ! -z "$t" ]
    then
        echo "${t//coog-/}"
    else
        local b; b=$(git rev-parse --abbrev-ref HEAD)
        local c; c=$(git rev-parse --short HEAD)
        echo "$b-$c" | sed -e "s/coog-//g"
    fi
}

deps() {
    pacman -S \
        mingw-w64-i686-librsvg \
        mingw-w64-i686-nsis \
        mingw-w64-i686-python3 \
        mingw-w64-i686-python3-setuptools \
        mingw-w64-i686-python3-pip \
        mingw-w64-i686-gtk3 \
        mingw-w64-i686-python3-gobject \
        mingw-w64-i686-gtksourceview3 \
        mingw-w64-i686-gtkglext \
        mingw-w64-i686-python3-cx_Freeze \
        mingw-w64-i686-gobject-introspection \
        mingw-w64-i686-goocanvas \
        mingw-w64-i686-gtksourceview3 \
        mingw-w64-i686-evince

    pip install \
      python-dateutil \
      chardet \
      pyflakes

    echo "gdrive should be installed from https://github.com/glotlabs/gdrive#downloads"
    echo "gdrive should be placed in a PATH folder"
}

clean() {
    rm -rf build dist coog-*
}

patch() {
    git apply win-patch.diff
    [ ! -z "$1" ] && echo "__version_coog__ = '$v'" >> tryton/__init__.py
}

unpatch() {
    git checkout HEAD -- tryton
}

build() {
    clean
    local v; v=$(version)
    python setup.py compile_catalog
    python setup-freeze.py install_exe -d dist
    makensis -DVERSION="$v" -DBITS=32 -DSERIES="$v" setup.nsi
    makensis -DVERSION="$v" -DBITS=32 setup-single.nsi
}

upload() {
    for f in ./coog-*
    do
        gdrive upload -p "$GDRIVE_FOLDER_ID" "$f"
    done
}

main() {
    [ -z "$1" ] && echo missing command && return 1
    "$1" "$@"
}

main "$@"
