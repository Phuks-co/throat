import u from "./Util";

u.ready(() => {
  // Badges that are svgs will get inlined so you can muck with them in CSS.
  document.querySelectorAll(".profilebadge>img").forEach((element) => {
    if (!element.attributes.src.value.endsWith(".svg")) {
      return;
    }
    let imgID = element.id;
    let imgClass = element.className;
    let imgURL = element.src;

    fetch(imgURL)
      .then((response) => {
        return response.text();
      })
      .then((text) => {
        let parser = new DOMParser();
        let xmlDoc = parser.parseFromString(text, "text/xml");

        // Get the SVG tag, ignore the rest
        let svg = xmlDoc.getElementsByTagName("svg")[0];

        // Add replaced image's ID to the new SVG
        if (typeof imgID !== "undefined") {
          svg.setAttribute("id", imgID);
        }
        // Add replaced image's classes to the new SVG
        if (typeof imgClass !== "undefined") {
          svg.setAttribute("class", imgClass + " replaced-svg");
        }

        // Remove any invalid XML tags as per http://validator.w3.org
        svg.removeAttribute("xmlns:a");

        // Check if the viewport is set, if the viewport is not set the SVG wont't scale.
        if (
          !svg.getAttribute("viewBox") &&
          svg.getAttribute("height") &&
          svg.getAttribute("width")
        ) {
          svg.setAttribute(
            "viewBox",
            "0 0 " +
              svg.getAttribute("height") +
              " " +
              svg.getAttribute("width")
          );
        }

        // Replace image with new SVG
        element.parentNode.replaceChild(svg, element);
      });
  });
});
