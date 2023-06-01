#!/bin/sh
#
# This builds a completely statically linked version of ffmpeg using musl-libc. This makes it start faster, which greatly
# improves performance when encoding many tiny files and launching 1 million instances of it.
# 
# You need musl-gcc available. This can be installed from the `musl` package on arch linux and probably other distros.
# If you can't use musl, remove the relevant parts.
#
# This is based on (heavily modified from) https://github.com/zimbatm/ffmpeg-static/blob/master/build.sh
#
# Download the ffmpeg, lame, and opus sources and put them in the build directory before running.
# Replace znver3 on line 70 with your cpu type (if different)
#

if [ -z "$ENV_ROOT" ]; then
  ENV_ROOT=$(pwd)
  export ENV_ROOT
fi

if [ -z "$ENV_ROOT" ]; then
  echo "Missing ENV_ROOT variable" >&2
elif [ "${ENV_ROOT#/}" = "$ENV_ROOT" ]; then
  echo "ENV_ROOT must be an absolute path" >&2
else

  BUILD_DIR="${BUILD_DIR:-$ENV_ROOT/build}"
  TARGET_DIR="${TARGET_DIR:-$ENV_ROOT/target}"
  BIN_DIR="${BIN_DIR:-$ENV_ROOT/bin}"

  export LDFLAGS="-L${TARGET_DIR}/lib"
  export DYLD_LIBRARY_PATH="${TARGET_DIR}/lib"
  export PKG_CONFIG_PATH="$TARGET_DIR/lib/pkgconfig"
  #export CFLAGS="-I${TARGET_DIR}/include $LDFLAGS -static-libgcc -Wl,-Bstatic -lc"
  export CC="musl-gcc"
  export CFLAGS="-march=native -O3 -I${TARGET_DIR}/include $LDFLAGS"
  export MAKEFLAGS="-j$(nproc)"
  export PATH="${TARGET_DIR}/bin:${PATH}"
  # Force PATH cache clearing
  hash -r
fi
rebuild=0

set -e
set -u

mkdir -p "$BUILD_DIR" "$TARGET_DIR" "$BIN_DIR"

echo "*** Building opus ***"
cd "$BUILD_DIR"/opus*
[ "$rebuild" -eq 1 -a -f Makefile ] && make distclean || true
[ ! -f config.status ] && ./configure --prefix="$TARGET_DIR" --disable-shared
make
make install

echo "*** Building mp3lame ***"
cd "$BUILD_DIR"/lame*
# The lame build script does not recognize aarch64, so need to set it manually
[ "$rebuild" -eq 1 -a -f Makefile ] && make distclean || true
[ ! -f config.status ] && ./configure --prefix="$TARGET_DIR" --enable-nasm --disable-shared
make
make install

echo "*** Building FFmpeg ***"
cd "$BUILD_DIR"/FFmpeg*
[ "$rebuild" -eq 1 -a -f Makefile ] && make distclean || true
[ ! -f config.status ] && PATH="$BIN_DIR:$PATH" \
PKG_CONFIG_PATH="$TARGET_DIR/lib/pkgconfig" ./configure \
  --prefix="$TARGET_DIR" \
  --pkg-config-flags="--static" \
  --cpu="znver3" \
  --cc="musl-gcc" \
  --extra-cflags="$CFLAGS" \
  --extra-ldflags="$LDFLAGS" \
  --extra-libs="-lpthread -lm" \
  --extra-ldexeflags="-static" \
  --bindir="$BIN_DIR" \
  --enable-stripping \
  --enable-cross-compile \
  --enable-gpl \
  --enable-version3 \
  --enable-libmp3lame \
  --enable-libopus \
  --enable-nonfree \
  --disable-ffplay \
  --disable-doc \
  --disable-debug \
  --disable-network \
  --disable-alsa \
  --disable-appkit \
  --disable-avfoundation \
  --disable-bzlib \
  --disable-coreimage \
  --disable-iconv \
  --disable-sndio \
  --disable-schannel \
  --disable-sdl2 \
  --disable-securetransport \
  --disable-vulkan \
  --disable-xlib \
  --disable-zlib \
  --disable-amf \
  --disable-audiotoolbox \
  --disable-cuda-llvm \
  --disable-cuvid \
  --disable-d3d11va \
  --disable-dxva2 \
  --disable-ffnvcodec \
  --disable-nvenc \
  --disable-nvdec \
  --disable-v4l2-m2m \
  --disable-vaapi \
  --disable-vdpau \
  --disable-videotoolbox

PATH="$BIN_DIR:$PATH" make
make install
make distclean
hash -r
