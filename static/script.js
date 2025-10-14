document.addEventListener("DOMContentLoaded", function() {
    const video = document.getElementById("qr-video");
    const status = document.getElementById("qr-status");

    navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false })
        .then(stream => {
            video.srcObject = stream;
            video.muted = true;
            video.setAttribute("playsinline", true);
            video.play();
            status.innerText = "Camera initialized. Check video feed!";
        })
        .catch(err => {
            status.innerText = "Camera error: " + err;
        });
});
