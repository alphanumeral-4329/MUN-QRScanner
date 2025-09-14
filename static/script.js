document.getElementById('loginForm').addEventListener('submit', function(event) {
    // Optional frontend validation or animation
    const ocid = document.getElementById('ocid').value;
    const password = document.getElementById('password').value;

    if (!ocid || !password) {
        event.preventDefault();
        alert('Please enter your OC ID and password.');
    }
});
