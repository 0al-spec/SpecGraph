(function () {
  const slides = Array.from(document.querySelectorAll("[data-slide]"));
  const prevButton = document.getElementById("prevSlide");
  const nextButton = document.getElementById("nextSlide");
  const slideCount = document.getElementById("slideCount");
  const progressBar = document.getElementById("progressBar");
  let activeIndex = 0;

  function formatIndex(index) {
    return String(index + 1).padStart(2, "0");
  }

  function updateSlide(nextIndex) {
    activeIndex = Math.max(0, Math.min(nextIndex, slides.length - 1));

    slides.forEach((slide, index) => {
      slide.classList.toggle("is-active", index === activeIndex);
      slide.setAttribute("aria-hidden", String(index !== activeIndex));
    });

    prevButton.disabled = activeIndex === 0;
    nextButton.disabled = activeIndex === slides.length - 1;
    slideCount.value = `${formatIndex(activeIndex)} / ${formatIndex(slides.length - 1)}`;
    slideCount.textContent = `${formatIndex(activeIndex)} / ${formatIndex(slides.length - 1)}`;
    progressBar.style.width = `${((activeIndex + 1) / slides.length) * 100}%`;

    const activeSlide = slides[activeIndex];
    if (activeSlide && window.location.hash !== `#${activeSlide.id}`) {
      history.replaceState(null, "", `#${activeSlide.id}`);
    }
  }

  function slideFromHash() {
    const hash = window.location.hash.replace("#", "");
    const index = slides.findIndex((slide) => slide.id === hash);
    return index >= 0 ? index : 0;
  }

  prevButton.addEventListener("click", () => updateSlide(activeIndex - 1));
  nextButton.addEventListener("click", () => updateSlide(activeIndex + 1));

  document.addEventListener("keydown", (event) => {
    if (event.defaultPrevented) return;

    switch (event.key) {
      case "ArrowLeft":
      case "PageUp":
        event.preventDefault();
        updateSlide(activeIndex - 1);
        break;
      case "ArrowRight":
      case "PageDown":
      case " ":
        event.preventDefault();
        updateSlide(activeIndex + 1);
        break;
      case "Home":
        event.preventDefault();
        updateSlide(0);
        break;
      case "End":
        event.preventDefault();
        updateSlide(slides.length - 1);
        break;
      default:
        break;
    }
  });

  window.addEventListener("hashchange", () => updateSlide(slideFromHash()));
  updateSlide(slideFromHash());
})();

