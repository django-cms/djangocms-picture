(function () {
    "use strict";

    function initializePicker(root) {
        if (root.dataset.frontifyInitialized === "true") {
            return;
        }
        root.dataset.frontifyInitialized = "true";

        var input = root.querySelector("textarea");
        var selectButton = root.querySelector("[data-frontify-select]");
        var clearButton = root.querySelector("[data-frontify-clear]");
        var preview = root.querySelector("[data-frontify-preview]");
        var previewContainer = root.querySelector(".djangocms-picture-frontify-preview");
        var label = root.querySelector("[data-frontify-label]");
        var mount = root.querySelector("[data-frontify-mount]");

        selectButton.addEventListener("click", async function () {
            if (!window.FrontifyFinder || !window.FrontifyFinder.create) {
                throw new Error("Frontify Finder failed to load.");
            }
            var finder = await window.FrontifyFinder.create({
                clientId: root.dataset.clientId,
                domain: root.dataset.domain,
                options: {
                    allowMultiSelect: false,
                    permanentDownloadUrls: true
                }
            });
            finder.onAssetsChosen(function (assets) {
                var asset = assets[0];
                input.value = JSON.stringify(asset);
                input.dispatchEvent(new Event("change", {bubbles: true}));
                preview.src = (asset.previewUrl || "").split("?")[0];
                label.textContent = asset.title || asset.name || asset.id;
                previewContainer.hidden = false;
                clearButton.hidden = false;
                finder.close();
            });
            finder.onCancel(function () {
                finder.close();
            });
            finder.mount(mount);
        });

        clearButton.addEventListener("click", function () {
            input.value = "";
            input.dispatchEvent(new Event("change", {bubbles: true}));
            preview.src = "";
            label.textContent = "";
            previewContainer.hidden = true;
            clearButton.hidden = true;
        });
    }

    function initialize() {
        document.querySelectorAll("[data-frontify-picker]").forEach(initializePicker);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
}());
