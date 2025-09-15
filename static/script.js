document.getElementById('loginForm').addEventListener('submit', function(event) {
    const ocid = document.getElementById('ocid').value;
    const password = document.getElementById('password').value;

    if (!ocid || !password) {
        event.preventDefault();
        alert('Please enter your OC ID and password.');
    }
});
