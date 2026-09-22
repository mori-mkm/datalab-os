# Run from repo root. Starts the Control Plane dev server.
Push-Location apps\control-plane
try {
    npm run dev
} finally {
    Pop-Location
}
