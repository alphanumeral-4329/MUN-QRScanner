<script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js"></script>
<script>
    document.addEventListener("DOMContentLoaded", function() {
        const video = document.getElementById("qr-video");
        const canvas = document.getElementById("qr-canvas");
        const ctx = canvas.getContext("2d");
        const status = document.getElementById("qr-status");

        let last_scanned = "";
        let last_scantime = 0;
        navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment"} })
        .then(stream => {
            video.srcObject = stream;
            video.setAttribute("playsinline", true);
            video.play();
            
