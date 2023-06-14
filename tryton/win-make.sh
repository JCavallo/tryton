#!/bin/bash

# For build
CERTIFICAT_PASSWORD=$2
WINDOWS_USER_PASSWORD=$3

# For upload
GITHUB_TOKEN=$2

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

build() {
    clean
    local v; v=$(version)
    python setup.py compile_catalog
    python setup-freeze.py install_exe -d dist
    "C:/PSTools/PsExec.exe" -u Administrator -p ${WINDOWS_USER_PASSWORD} "C:\msys32\home\Administrator\tryton\tryton\sign-client.bat" ${CERTIFICAT_PASSWORD}
    makensis -DVERSION="$v" -DBITS=32 -DSERIES="$v" setup.nsi
    # makensis -DVERSION="$v" -DBITS=32 setup-single.nsi
    mv dist "$v"
    "C:/PSTools/PsExec.exe" -u Administrator -p ${WINDOWS_USER_PASSWORD} "C:\msys32\home\Administrator\tryton\tryton\sign-client.bat" ${CERTIFICAT_PASSWORD}
    zip -q -9 -r "coog-$v.zip" "$v"
}

upload() {
    local v; v=$(version)

    CREATE_RELEASE=$(curl -L -X POST -H "Accept: application/vnd.github+json" -H "Authorization: Bearer ${GITHUB_TOKEN}" -H "X-GitHub-Api-Version: 2022-11-28" https://api.github.com/repos/coopengo/tryton/releases -d "{\"tag_name\":\"coog-$v\",\"name\":\"coog-$v\",\"body\":\"Coog client for coog-$v\",\"make_latest\":\"false\"}")
    UPLOAD_URL=$(echo "${CREATE_RELEASE}" | jq -r '.upload_url' | sed 's/{?name,label}//')

    for f in ./coog-*
    do
        curl -X POST -H "Content-Type: application/octet-stream" --data-binary "@${f/.\/}" -H "Authorization: Bearer ${GITHUB_TOKEN}" "${UPLOAD_URL}?name=${f/.\/}"
    done
}

upload() {
  for f in ./coog-*
  do
    aws --region "eu-central-1" s3 cp "$f" s3://coog-client/
  done
}

main() {
    [ -z "$1" ] && echo missing command && return 1
    "$1" "$@"
}

main "$@"
