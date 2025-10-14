document.addEventListener("DOMContentLoaded", function() {
    const video = document.getElementById("qr-video");
    const canvas = document.getElementById("qr-canvas");
    const ctx = canvas.getContext("2d");
    const status = document.getElementById("qr-status");

    let lastScanned = "";
    let lastScanTime = 0;

    navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
        .then(stream => {
            video.srcObject = stream;
            video.setAttribute("playsinline", true);
            video.play();
            requestAnimationFrame(tick);
        })
        .catch(err => {
            console.error("Camera error:", err);
            showFlash("Camera error: " + err, "error");
        });

    function tick() {
        if (video.readyState === video.HAVE_ENOUGH_DATA) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const code = jsQR(imageData.data, imageData.width, imageData.height);

            if (code) processQRCode(code.data);
        }
        requestAnimationFrame(tick);
    }

    async function processQRCode(data) {
        const now = Date.now();
        if (data === lastScanned && now - lastScanTime < 3000) return;
        lastScanned = data;
        lastScanTime = now;

        const match = data.match(/\/scan\/([^\/\s]+)/);
        const delegateId = match ? match[1] : data;

        status.innerText = "Scanning: " + delegateId;

        try {
            const response = await fetch(`/scan/${delegateId}`);
            const html = await response.text();

            const parser = new DOMParser();
            const doc = parser.parseFromString(html, "text/html");
            const newCard = doc.querySelector(".delegate-card");
            const oldCard = document.querySelector(".delegate-card");

            if (newCard) {
                if (oldCard) oldCard.replaceWith(newCard);
                else document.querySelector(".container").prepend(newCard);

                const alreadyScanned = newCard.querySelector(".scanned");
                if (alreadyScanned) {
                    showFlash(alreadyScanned.innerText, "warning");
                } else {
                    showFlash("Delegate scanned!", "success");
                }
            }
        } catch (err) {
            console.error(err);
            showFlash("Scan failed: " + err, "error");
        }
    }

    function showFlash(message, type="success") {
        const container = document.getElementById("flash-container");
        if (!container) return;

        const div = document.createElement("div");
        div.className = `flash-message flash-${type}`;
        div.innerText = message;
        container.appendChild(div);

        setTimeout(() => div.remove(), 3000);
    }
});
