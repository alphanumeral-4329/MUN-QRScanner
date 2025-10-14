<script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function() {
    const video = document.getElementById("qr-video");
    const canvas = document.getElementById("qr-canvas");
    const ctx = canvas.getContext("2d");
    const status = document.getElementById("qr-status");
    const flashContainer = document.getElementById("flash-container");
    const scannedDelegates = new Set();

navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false })
.then(stream => {
    video.srcObject = stream;
    video.muted = true;
    video.setAttribute("playsinline", true);
    video.play();
    requestAnimationFrame(tick);
})
.catch(err => { status.innerText = "Camera error: " + err; });


    function scanLoop() {
        if (video.readyState === video.HAVE_ENOUGH_DATA) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const code = jsQR(imageData.data, imageData.width, imageData.height);
            if (code) handleQRCode(code.data);
        }
        requestAnimationFrame(scanLoop);
    }

    async function handleQRCode(data) {
        const match = data.match(/\/scan\/([^\/\s]+)/);
        const delegateId = match ? match[1] : data;

        if (scannedDelegates.has(delegateId)) {
            showFlash(`Delegate ${delegateId} already scanned`, 'warning');
            return;
        }

        status.innerText = `Scanning: ${delegateId}`;

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
            }

            scannedDelegates.add(delegateId);
            showFlash(`Delegate ${delegateId} scanned successfully`, 'success');
        } catch (err) {
            showFlash(`Error scanning delegate ${delegateId}`, 'error');
        }
    }

    function showFlash(message, type='success') {
        const flash = document.createElement("div");
        flash.className = `flash-message flash-${type}`;
        flash.innerText = message;
        flashContainer.appendChild(flash);
        setTimeout(() => flash.remove(), 3000);
    }
});
</script>
