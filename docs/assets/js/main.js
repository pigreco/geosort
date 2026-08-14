// GeoSort docs — piccolo script condiviso (IT + EN), zero dipendenze.

// Segnala gli screenshot non ancora generati con un placeholder invece
// dell'icona di immagine rotta del browser.
document.querySelectorAll("figure.shot img").forEach(function (img) {
  img.addEventListener("error", function () {
    img.closest("figure.shot").classList.add("missing");
  });
});

// Evidenzia nella TOC laterale la sezione attualmente visibile.
(function () {
  var links = document.querySelectorAll("nav.toc a[href^='#']");
  if (!links.length || !("IntersectionObserver" in window)) return;
  var map = {};
  links.forEach(function (a) {
    map[a.getAttribute("href").slice(1)] = a;
  });
  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        var link = map[entry.target.id];
        if (!link) return;
        if (entry.isIntersecting) {
          links.forEach(function (a) { a.style.background = ""; a.style.color = ""; });
          link.style.background = "var(--accent-light)";
          link.style.color = "var(--accent)";
        }
      });
    },
    { rootMargin: "-10% 0px -80% 0px" }
  );
  document.querySelectorAll("main [id]").forEach(function (el) {
    observer.observe(el);
  });
})();
