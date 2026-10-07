document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("document");
  const info = document.getElementById("fileInfo");
  const form = document.getElementById("uploadForm");

  if (input) {
    input.addEventListener("change", () => {
      const file = input.files[0];
      if (!file) {
        info.textContent = "Choose a document to continue.";
        return;
      }
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      info.innerHTML = `<b>${file.name}</b> · ${sizeMB} MB`;
    });
  }

  if (form) {
    form.addEventListener("submit", () => {
      const button = form.querySelector("button");
      button.disabled = true;
      button.textContent = "HASHING + SIGNING...";
    });
  }
});
