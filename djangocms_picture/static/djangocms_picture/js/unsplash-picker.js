(function () {
    "use strict";

    var API_URL = "https://api.unsplash.com";

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
        var current = root.querySelector("[data-unsplash-current]");
        var values = photoValues(photo, root.dataset.applicationName);
        root.querySelector("[data-unsplash-preview]").src = values.previewUrl;
        root.querySelector("[data-unsplash-label]").textContent = values.label;
        root.querySelector("[data-unsplash-photographer]").textContent = values.photographerName;
        root.querySelector("[data-unsplash-photographer]").href = values.photographerUrl;
        root.querySelector("[data-unsplash-provider]").href = values.photoUrl;
        current.hidden = false;
        root.querySelector("[data-unsplash-clear]").hidden = false;
    }

    async function apiRequest(root, url) {
        var response = await fetch(url, {
            headers: {
                "Accept-Version": "v1",
                "Authorization": "Client-ID " + root.dataset.accessKey
            }
        });
        if (!response.ok) {
            var payload = await response.json().catch(function () { return {}; });
            var message = payload.errors && payload.errors.length
                ? payload.errors.join(" ")
                : "Unsplash request failed (" + response.status + ").";
            throw new Error(message);
        }
        return response.json();
    }

    async function trackSelection(root, photo) {
        var downloadLocation = photo.links && photo.links.download_location;
        if (!downloadLocation) {
            throw new Error("Unsplash did not return a download tracking URL.");
        }
        await apiRequest(root, downloadLocation);
    }

    function addAttribution(container, photo, applicationName) {
        var values = photoValues(photo, applicationName);
        var credit = document.createElement("small");
        credit.append(document.createTextNode("Photo by "));
        var photographer = document.createElement("a");
        photographer.href = values.photographerUrl;
        photographer.target = "_blank";
        photographer.rel = "noopener noreferrer";
        photographer.textContent = values.photographerName;
        credit.append(photographer, document.createTextNode(" on "));
        var provider = document.createElement("a");
        provider.href = values.photoUrl;
        provider.target = "_blank";
        provider.rel = "noopener noreferrer";
        provider.textContent = "Unsplash";
        credit.append(provider);
        container.append(credit);
    }

    function renderResults(root, photos) {
        var results = root.querySelector("[data-unsplash-results]");
        results.replaceChildren();
        photos.forEach(function (photo) {
            var item = document.createElement("div");
            item.className = "djangocms-picture-unsplash-result";
            var select = document.createElement("button");
            select.type = "button";
            select.title = photo.alt_description || photo.description || "Select Unsplash photo";
            var image = document.createElement("img");
            image.src = photo.urls.thumb;
            image.alt = photo.alt_description || "";
            image.loading = "lazy";
            select.append(image);
            select.addEventListener("click", async function () {
                var status = root.querySelector("[data-unsplash-status]");
                select.disabled = true;
                status.textContent = "Selecting image…";
                try {
                    await trackSelection(root, photo);
                    var input = root.querySelector("textarea");
                    input.value = JSON.stringify(photo);
                    input.dispatchEvent(new Event("change", {bubbles: true}));
                    updateCurrent(root, photo);
                    status.textContent = "Image selected.";
                } catch (error) {
                    status.textContent = error.message;
                } finally {
                    select.disabled = false;
                }
            });
            item.append(select);
            addAttribution(item, photo, root.dataset.applicationName);
            results.append(item);
        });
    }

    async function search(root) {
        var query = root.querySelector("[data-unsplash-query]").value.trim();
        var status = root.querySelector("[data-unsplash-status]");
        var searchButton = root.querySelector("[data-unsplash-search]");
        if (!query) {
            status.textContent = "Enter a search term.";
            return;
        }

        var url = new URL(API_URL + "/search/photos");
        url.searchParams.set("query", query);
        url.searchParams.set("per_page", root.dataset.perPage);
        url.searchParams.set("content_filter", root.dataset.contentFilter);
        if (root.dataset.orientation) {
            url.searchParams.set("orientation", root.dataset.orientation);
        }

        searchButton.disabled = true;
        status.textContent = "Searching…";
        try {
            var payload = await apiRequest(root, url);
            renderResults(root, payload.results || []);
            status.textContent = payload.results && payload.results.length
                ? payload.results.length + " images found."
                : "No images found.";
        } catch (error) {
            status.textContent = error.message;
        } finally {
            searchButton.disabled = false;
        }
    }

    function initializePicker(root) {
        if (root.dataset.unsplashInitialized === "true") {
            return;
        }
        root.dataset.unsplashInitialized = "true";
        var query = root.querySelector("[data-unsplash-query]");
        root.querySelector("[data-unsplash-search]").addEventListener("click", function () {
            search(root);
        });
        query.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                search(root);
            }
        });
        root.querySelector("[data-unsplash-clear]").addEventListener("click", function () {
            var input = root.querySelector("textarea");
            input.value = "";
            input.dispatchEvent(new Event("change", {bubbles: true}));
            root.querySelector("[data-unsplash-preview]").src = "";
            root.querySelector("[data-unsplash-current]").hidden = true;
            root.querySelector("[data-unsplash-clear]").hidden = true;
        });
    }

    function initialize() {
        document.querySelectorAll("[data-unsplash-picker]").forEach(initializePicker);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
}());
