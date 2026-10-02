#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "=== Termux Code Installer ==="

pkg update -y
pkg install -y python git curl cmake clang make

cd "$HOME"

if [ -d "$HOME/termux-code/.git" ]; then
    git -C "$HOME/termux-code" pull --ff-only
else
    git clone https://github.com/siggmaez/Termux-Code.git "$HOME/termux-code"
fi

LOCAL="$HOME/termux-code-local"
LLAMA="$LOCAL/llama.cpp"
MODELS="$LOCAL/models"

mkdir -p "$MODELS"

if [ -d "$LLAMA/.git" ]; then
    git -C "$LLAMA" pull --ff-only
else
    git clone --depth 1 https://github.com/ggml-org/llama.cpp.git "$LLAMA"
fi

cmake -S "$LLAMA" -B "$LLAMA/build" \
    -DCMAKE_BUILD_TYPE=Release \
    -DGGML_OPENMP=OFF

cmake --build "$LLAMA/build" -j2 --target llama-server

MODEL="$MODELS/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"

if [ ! -f "$MODEL" ]; then
    curl -L --fail --progress-bar \
        -o "$MODEL.part" \
        "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"

    mv "$MODEL.part" "$MODEL"
fi

cat > "$PREFIX/bin/termux-code" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd "$HOME/termux-code"
exec python termux_code.py
EOF

chmod +x "$PREFIX/bin/termux-code"

echo
echo "=============================="
echo "Установка завершена"
echo "Запуск: termux-code"
echo
echo "Внутри Termux Code:"
echo "/local start"
echo "/local status"
echo "/mode local"
echo "=============================="
