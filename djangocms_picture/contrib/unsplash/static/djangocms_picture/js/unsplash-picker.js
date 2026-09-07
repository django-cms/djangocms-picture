(function () {
    "use strict";

    function attributionUrl(url, applicationName) {
        var result = new URL(url);
        result.searchParams.set("utm_source", applicationName);
        result.searchParams.set("utm_medium", "referral");
        return result.toString();
    }

    function photoValues(photo, applicationName) {
        var normalized = Boolean(photo.preview_url);
        var attribution = photo.attribution || {};
        var user = photo.user || {};
        var links = photo.links || {};
        var userLinks = user.links || {};
        return {
            previewUrl: photo.preview_url || (photo.urls || {}).small || "",
            label: photo.label || photo.description || photo.alt_description || photo.id || "",
            photographerName: attribution.creator_name || user.name || "",
            photographerUrl: normalized
                ? attribution.creator_url
                : attributionUrl(userLinks.html, applicationName),
            photoUrl: normalized
                ? attribution.provider_url
                : attributionUrl(links.html, applicationName)
        };
    }

    function updateCurrent(root, photo) {
        var values = photoValues(photo, root.dataset.applicationName);
        root.querySelector("[data-unsplash-preview]").src = values.previewUrl;
        root.querySelector("[data-unsplash-label]").textContent = values.label;
        root.querySelector("[data-unsplash-photographer]").textContent = values.photographerName;
        root.querySelector("[data-unsplash-photographer]").href = values.photographerUrl;
        root.querySelector("[data-unsplash-provider]").href = values.photoUrl;
        root.querySelector("[data-unsplash-current]").hidden = false;
        root.querySelector("[data-unsplash-clear]").hidden = false;
    }

    function openPicker(root) {
        var input = root.querySelector("textarea");
        var url = new URL(root.dataset.pickerUrl, window.location.href);
        url.searchParams.set("field_id", input.id);
        url.searchParams.set("_popup", "1");
        window.open(
            url.toString(),
            "djangocms_picture_unsplash_" + input.id,
            "height=760,width=1100,resizable=yes,scrollbars=yes"
        );
    }

    function clearPicker(root) {
        var input = root.querySelector("textarea");
        input.value = "";
        input.dispatchEvent(new Event("change", {bubbles: true}));
        root.querySelector("[data-unsplash-preview]").src = "";
        root.querySelector("[data-unsplash-current]").hidden = true;
        root.querySelector("[data-unsplash-clear]").hidden = true;
    }

    document.addEventListener("click", function (event) {
        var openButton = event.target.closest("[data-unsplash-open]");
        if (openButton) {
            openPicker(openButton.closest("[data-unsplash-picker]"));
            return;
        }
        var clearButton = event.target.closest("[data-unsplash-clear]");
        if (clearButton) {
            clearPicker(clearButton.closest("[data-unsplash-picker]"));
        }
    });

    window.addEventListener("message", function (event) {
        if (event.origin !== window.location.origin) {
            return;
        }
        var message = event.data || {};
        if (message.type !== "djangocms-picture:unsplash-selected" || !message.fieldId) {
            return;
        }
        var input = document.getElementById(message.fieldId);
        if (!input) {
            return;
        }
        var root = input.closest("[data-unsplash-picker]");
        if (!root) {
            return;
        }
        input.value = JSON.stringify(message.photo);
        input.dispatchEvent(new Event("change", {bubbles: true}));
        updateCurrent(root, message.photo);
    });
}());
