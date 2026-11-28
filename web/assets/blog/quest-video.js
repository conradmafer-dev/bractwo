"use strict";

for (const videos of document.querySelectorAll(".quest-videos")) {
  const player = videos.querySelector(".quest-player");

  for (const link of videos.querySelectorAll("[data-quest-video]")) {
    link.addEventListener("click", (event) => {
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();

      const frame = document.createElement("iframe");
      frame.src = "https://www.youtube-nocookie.com/embed/" + link.dataset.questVideo;
      frame.title = link.textContent;
      frame.allow = "encrypted-media; fullscreen; picture-in-picture";
      frame.allowFullscreen = true;
      frame.referrerPolicy = "strict-origin-when-cross-origin";

      const watch = document.createElement("a");
      watch.href = link.href;
      watch.textContent = videos.dataset.watchLabel;
      player.replaceChildren(frame, watch);
      frame.focus();
    });
  }
}
