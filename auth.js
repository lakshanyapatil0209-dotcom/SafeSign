document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("loginForm");
  if (form) {
    form.addEventListener("submit", () => {
      const button = form.querySelector("button");
      if (button) {
        button.disabled = true;
        button.textContent = "AUTHENTICATING...";
      }
    });
  }
});
