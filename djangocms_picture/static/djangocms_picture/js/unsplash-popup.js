(function () {
    "use strict";

    var API_URL = "https://api.unsplash.com";

    function attributionUrl(url, applicationName) {
        var result = new URL(url);
        result.searchParams.set("utm_source", applicationName);
        result.searchParams.set("utm_medium", "referral");
        return result.toString();
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

    function addAttribution(container, root, photo) {
        var credit = document.createElement("small");
        credit.append(document.createTextNode("Photo by "));
        var photographer = document.createElement("a");
        photographer.href = attributionUrl(photo.user.links.html, root.dataset.applicationName);
        photographer.target = "_blank";
        photographer.rel = "noopener noreferrer";
        photographer.textContent = photo.user.name;
        credit.append(photographer, document.createTextNode(" on "));
        var provider = document.createElement("a");
        provider.href = attributionUrl(photo.links.html, root.dataset.applicationName);
        provider.target = "_blank";
        provider.rel = "noopener noreferrer";
        provider.textContent = "Unsplash";
        credit.append(provider);
        container.append(credit);
    }

    function selectPhoto(root, photo, button) {
        var status = root.querySelector("[data-unsplash-status]");
        button.disabled = true;
        status.textContent = "Selecting image…";
        trackSelection(root, photo).then(function () {
            if (!window.opener) {
                throw new Error("The editor window is no longer available.");
            }
            window.opener.postMessage(
                {
                    type: "djangocms-picture:unsplash-selected",
                    fieldId: root.dataset.fieldId,
                    photo: photo
                },
                window.location.origin
            );
            window.close();
        }).catch(function (error) {
            status.textContent = error.message;
            button.disabled = false;
        });
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
            select.addEventListener("click", function () {
                selectPhoto(root, photo, select);
            });
            item.append(select);
            addAttribution(item, root, photo);
            results.append(item);
        });
    }

    function updatePagination(root, page, totalPages) {
        var pagination = root.querySelector("[data-unsplash-pagination]");
        pagination.hidden = totalPages <= 1;
        root.querySelector("[data-unsplash-page]").textContent = page + " / " + totalPages;
        root.querySelector("[data-unsplash-previous]").disabled = page <= 1;
        root.querySelector("[data-unsplash-next]").disabled = page >= totalPages;
        root.dataset.page = String(page);
        root.dataset.totalPages = String(totalPages);
    }

    async function search(root, page) {
        var query = root.querySelector("[data-unsplash-query]").value.trim();
        var status = root.querySelector("[data-unsplash-status]");
        var searchButton = root.querySelector("[data-unsplash-search]");
        if (!query) {
            status.textContent = "Enter a search term.";
            return;
        }

        var url = new URL(API_URL + "/search/photos");
        url.searchParams.set("query", query);
        url.searchParams.set("page", page);
        url.searchParams.set("per_page", root.dataset.perPage);
        url.searchParams.set("content_filter", root.dataset.contentFilter);
        ["orientation", "color", "order_by"].forEach(function (name) {
            var value = root.querySelector('[name="' + name + '"]').value;
            if (value) {
                url.searchParams.set(name, value);
            }
        });
        if (root.dataset.collections) {
            url.searchParams.set("collections", root.dataset.collections);
        }

        searchButton.disabled = true;
        status.textContent = "Searching…";
        try {
            var payload = await apiRequest(root, url);
            renderResults(root, payload.results || []);
            updatePagination(root, page, payload.total_pages || 1);
            status.textContent = payload.results && payload.results.length
                ? payload.total + " images found."
                : "No images found.";
        } catch (error) {
            status.textContent = error.message;
        } finally {
            searchButton.disabled = false;
        }
    }

    function initialize(root) {
        root.querySelector("[data-unsplash-search-form]").addEventListener("submit", function (event) {
            event.preventDefault();
            search(root, 1);
        });
        root.querySelector("[data-unsplash-previous]").addEventListener("click", function () {
            search(root, Number(root.dataset.page) - 1);
        });
        root.querySelector("[data-unsplash-next]").addEventListener("click", function () {
            search(root, Number(root.dataset.page) + 1);
        });
    }

    document.querySelectorAll("[data-unsplash-popup]").forEach(initialize);
}());
