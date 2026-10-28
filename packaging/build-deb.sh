#!/usr/bin/env bash
# Build unzzz .deb packages for amd64 and arm64 without debhelper.
# The application is pure Python, so both packages carry the same payload.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(PYTHONPATH="$ROOT" python3 -c 'from unzzz import __version__; print(__version__)')"
OUT="$ROOT/dist"
BUILD="$ROOT/build/deb"
if [ "$#" -eq 0 ]; then
  ARCHES=(amd64 arm64)
else
  ARCHES=("$@")
fi

rm -rf "$BUILD"
mkdir -p "$OUT" "$BUILD"

for ARCH in "${ARCHES[@]}"; do
  case "$ARCH" in amd64|arm64) ;; *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;; esac
  STAGE="$BUILD/$ARCH"
  mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/lib/unzzz/bin" "$STAGE/usr/bin" \
    "$STAGE/usr/lib/systemd/system" "$STAGE/usr/share/doc/unzzz/docs" \
    "$STAGE/usr/share/doc/unzzz/examples"

  cp -a "$ROOT/unzzz" "$STAGE/usr/lib/unzzz/unzzz"
  find "$STAGE/usr/lib/unzzz" -name '__pycache__' -type d -prune -exec rm -rf {} +
  find "$STAGE/usr/lib/unzzz" -name '*.pyc' -delete
  install -m 0755 "$ROOT/bin/unzzz" "$STAGE/usr/lib/unzzz/bin/unzzz"
  ln -s /usr/lib/unzzz/bin/unzzz "$STAGE/usr/bin/unzzz"
  install -m 0644 "$ROOT/packaging/debian/unzzz.service" "$STAGE/usr/lib/systemd/system/unzzz.service"
  install -m 0644 "$ROOT/README.md" "$STAGE/usr/share/doc/unzzz/README.md"
  install -m 0644 "$ROOT/LICENSE" "$STAGE/usr/share/doc/unzzz/copyright"
  install -m 0644 "$ROOT/docs/special-days-example.csv" "$STAGE/usr/share/doc/unzzz/examples/special-days-example.csv"
  cp -a "$ROOT/docs/." "$STAGE/usr/share/doc/unzzz/docs/"
  { echo "unzzz ($VERSION) unstable; urgency=medium"; echo; echo "  * Release $VERSION."; echo; echo " -- unzzz maintainers <unzzz@localhost>  $(date -R)"; } \
    > "$STAGE/usr/share/doc/unzzz/changelog"

  SIZE="$(du -sk "$STAGE" | awk '{print $1}')"
  sed -e "s/@VERSION@/$VERSION/g" -e "s/@ARCH@/$ARCH/g" -e "s/@SIZE@/$SIZE/g" \
    "$ROOT/packaging/debian/control.in" > "$STAGE/DEBIAN/control"
  install -m 0755 "$ROOT/packaging/debian/postinst" "$STAGE/DEBIAN/postinst"
  install -m 0755 "$ROOT/packaging/debian/prerm" "$STAGE/DEBIAN/prerm"
  install -m 0755 "$ROOT/packaging/debian/postrm" "$STAGE/DEBIAN/postrm"
  chown -R root:root "$STAGE"
  chmod -R u=rwX,go=rX "$STAGE"
  chmod 0755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/prerm" "$STAGE/DEBIAN/postrm"

  (cd "$STAGE" && find . -type f ! -path './DEBIAN/*' -printf '%P\0' \
    | sort -z | xargs -0 md5sum > DEBIAN/md5sums)
  chmod 0644 "$STAGE/DEBIAN/md5sums"

  dpkg-deb --build --root-owner-group "$STAGE" "$OUT/unzzz_${VERSION}_${ARCH}.deb"
  echo "built $OUT/unzzz_${VERSION}_${ARCH}.deb"
done

rm -rf "$BUILD"
