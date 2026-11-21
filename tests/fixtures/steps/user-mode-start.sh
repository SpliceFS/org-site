# Fixture user-mode-start: a here document.
cat > "$HOME/example.yaml" <<'EOF'
url: "https://east.example.com/api"
EOF
example-client
