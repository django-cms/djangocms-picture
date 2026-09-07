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
        var downloadLocation = photo.download_location
            || (photo.links && photo.links.download_location);
        if (!downloadLocation) {
            throw new Error("Unsplash did not return a download tracking URL.");
        }
        await apiRequest(root, downloadLocation);
    }

    function addAttribution(container, root, photo) {
        var stored = photo.attribution || {};
        var user = photo.user || {};
        var userLinks = user.links || {};
        var links = photo.links || {};
        var photographerName = stored.creator_name || user.name;
        var photographerUrl = stored.creator_url || userLinks.html;
        var providerUrl = stored.provider_url || links.html;
        if (!photographerName || !photographerUrl || !providerUrl) {
            return;
        }
        var credit = document.createElement("small");
        credit.append(document.createTextNode("Photo by "));
        var photographer = document.createElement("a");
        photographer.href = attributionUrl(photographerUrl, root.dataset.applicationName);
        photographer.target = "_blank";
        photographer.rel = "noopener noreferrer";
        photographer.textContent = photographerName;
        credit.append(photographer, document.createTextNode(" on "));
        var provider = document.createElement("a");
        provider.href = attributionUrl(providerUrl, root.dataset.applicationName);
        provider.target = "_blank";
        provider.rel = "noopener noreferrer";
        provider.textContent = "Unsplash";
        credit.append(provider);
        container.append(credit);
    }

    function photoUrl(photo) {
        var urls = photo.urls || {};
        return photo.raw_url || urls.raw || photo.preview_url || urls.regular
            || urls.small || photo.full_url || urls.full || "";
    }

    function currentTransform(root) {
        var qualityValue = root.querySelector("[data-unsplash-quality]").value;
        return {
            crop_mode: root.querySelector("[data-unsplash-crop-mode]").value,
            focal_point: {
                x: Number(root.querySelector("[data-unsplash-focal-x]").value),
                y: Number(root.querySelector("[data-unsplash-focal-y]").value)
            },
            format: root.querySelector("[data-unsplash-format]").value,
            quality: qualityValue === "" ? null : Number(qualityValue)
        };
    }

    function sourcePreviewUrl(root, photo) {
        var source = photoUrl(photo);
        if (!source) {
            return "";
        }
        var transform = currentTransform(root);
        var url = new URL(source);
        ["w", "h", "fit", "crop", "fp-x", "fp-y", "fm", "q"].forEach(function (name) {
            url.searchParams.delete(name);
        });
        url.searchParams.set("w", "1200");
        url.searchParams.set("fit", "max");
        if (transform.format) {
            url.searchParams.set("fm", transform.format);
        }
        if (transform.quality !== null) {
            url.searchParams.set("q", transform.quality);
        }
        return url.toString();
    }

    function positionFocalCircle(root) {
        var transform = currentTransform(root);
        var circle = root.querySelector("[data-unsplash-focal-circle]");
        circle.style.left = (transform.focal_point.x * 100) + "%";
        circle.style.top = (transform.focal_point.y * 100) + "%";
        circle.setAttribute(
            "aria-valuenow",
            String(Math.round(transform.focal_point.x * 100))
        );
        circle.setAttribute(
            "aria-valuetext",
            Math.round(transform.focal_point.x * 100) + "% horizontal, "
                + Math.round(transform.focal_point.y * 100) + "% vertical"
        );
    }

    function updateTransformControls(root) {
        positionFocalCircle(root);
        if (root.selectedPhoto) {
            var sourceImage = root.querySelector("[data-unsplash-selected-image]");
            var sourceUrl = sourcePreviewUrl(root, root.selectedPhoto);
            if (sourceImage.src !== sourceUrl) {
                sourceImage.src = sourceUrl;
            }
        }
    }

    function setFocalPoint(root, x, y) {
        root.querySelector("[data-unsplash-focal-x]").value = String(
            Math.max(0, Math.min(1, x))
        );
        root.querySelector("[data-unsplash-focal-y]").value = String(
            Math.max(0, Math.min(1, y))
        );
        root.querySelector("[data-unsplash-crop-mode]").value = "focalpoint";
        updateTransformControls(root);
    }

    function moveFocalPoint(root, event) {
        var editor = root.querySelector("[data-unsplash-focal-editor]");
        var bounds = editor.getBoundingClientRect();
        if (!bounds.width || !bounds.height) {
            return;
        }
        setFocalPoint(
            root,
            (event.clientX - bounds.left) / bounds.width,
            (event.clientY - bounds.top) / bounds.height
        );
    }

    function sizeFocalEditor(root) {
        var editor = root.querySelector("[data-unsplash-focal-editor]");
        var image = root.querySelector("[data-unsplash-selected-image]");
        if (!image.naturalWidth || !image.naturalHeight) {
            return;
        }
        var availableWidth = editor.parentElement.clientWidth;
        if (!availableWidth) {
            return;
        }
        var scale = Math.min(
            1,
            availableWidth / image.naturalWidth,
            250 / image.naturalHeight
        );
        editor.style.width = Math.floor(image.naturalWidth * scale) + "px";
    }

    function initializeFocalPoint(root) {
        var editor = root.querySelector("[data-unsplash-focal-editor]");
        var circle = root.querySelector("[data-unsplash-focal-circle]");
        var image = root.querySelector("[data-unsplash-selected-image]");
        image.addEventListener("load", function () {
            sizeFocalEditor(root);
        });
        window.addEventListener("resize", function () {
            sizeFocalEditor(root);
        });
        editor.addEventListener("pointerdown", function (event) {
            event.preventDefault();
            root.focalPointerId = event.pointerId;
            editor.setPointerCapture(event.pointerId);
            moveFocalPoint(root, event);
        });
        editor.addEventListener("pointermove", function (event) {
            if (root.focalPointerId === event.pointerId) {
                moveFocalPoint(root, event);
            }
        });
        function finishDrag(event) {
            if (root.focalPointerId === event.pointerId) {
                root.focalPointerId = null;
            }
        }
        editor.addEventListener("pointerup", finishDrag);
        editor.addEventListener("pointercancel", finishDrag);
        circle.addEventListener("keydown", function (event) {
            var transform = currentTransform(root);
            var x = transform.focal_point.x;
            var y = transform.focal_point.y;
            var step = event.shiftKey ? 0.1 : 0.01;
            if (event.key === "ArrowLeft") {
                x -= step;
            } else if (event.key === "ArrowRight") {
                x += step;
            } else if (event.key === "ArrowUp") {
                y -= step;
            } else if (event.key === "ArrowDown") {
                y += step;
            } else {
                return;
            }
            event.preventDefault();
            setFocalPoint(root, x, y);
        });
    }

    function setTransformControls(root, transform) {
        transform = transform || {};
        var focalPoint = transform.focal_point || {};
        root.querySelector("[data-unsplash-crop-mode]").value =
            transform.crop_mode || "entropy";
        root.querySelector("[data-unsplash-focal-x]").value =
            focalPoint.x === undefined ? "0.5" : String(focalPoint.x);
        root.querySelector("[data-unsplash-focal-y]").value =
            focalPoint.y === undefined ? "0.5" : String(focalPoint.y);
        root.querySelector("[data-unsplash-format]").value = transform.format || "";
        root.querySelector("[data-unsplash-quality]").value =
            transform.quality === null || transform.quality === undefined
                ? ""
                : String(transform.quality);
        updateTransformControls(root);
    }

    function markSelectedResult(root) {
        root.querySelectorAll("[data-unsplash-photo-id]").forEach(function (button) {
            button.setAttribute(
                "aria-pressed",
                String(Boolean(root.selectedPhoto) && button.dataset.unsplashPhotoId === root.selectedPhoto.id)
            );
        });
    }

    function previewPhoto(root, photo, options) {
        var selection = root.querySelector("[data-unsplash-selection]");
        var attribution = root.querySelector("[data-unsplash-selected-attribution]");
        root.selectedPhoto = photo;
        var selectedImage = root.querySelector("[data-unsplash-selected-image]");
        selectedImage.alt = photo.alt_text || photo.alt_description || photo.description || "";
        attribution.replaceChildren();
        addAttribution(attribution, root, photo);
        selection.hidden = false;
        setTransformControls(root, photo.transform);
        markSelectedResult(root);
        if (options && options.scroll) {
            selection.scrollIntoView({behavior: "smooth", block: "start"});
        }
    }

    function savePhoto(root) {
        var status = root.querySelector("[data-unsplash-status]");
        var button = root.querySelector("[data-unsplash-save]");
        var quality = root.querySelector("[data-unsplash-quality]");
        if (!root.selectedPhoto) {
            status.textContent = "Select an image first.";
            return;
        }
        if (!quality.checkValidity()) {
            quality.reportValidity();
            return;
        }
        var photo = Object.assign({}, root.selectedPhoto, {
            transform: currentTransform(root)
        });
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

    function initialPhoto(root) {
        if (!window.opener || !root.dataset.fieldId) {
            return null;
        }
        try {
            var field = window.opener.document.getElementById(root.dataset.fieldId);
            return field && field.value ? JSON.parse(field.value) : null;
        } catch (error) {
            return null;
        }
    }

    function renderResults(root, photos) {
        var results = root.querySelector("[data-unsplash-results]");
        results.replaceChildren();
        photos.forEach(function (photo) {
            var item = document.createElement("div");
            item.className = "djangocms-picture-unsplash-result";
            var select = document.createElement("button");
            select.type = "button";
            select.dataset.unsplashPhotoId = photo.id;
            select.setAttribute("aria-pressed", "false");
            select.title = photo.alt_description || photo.description || "Select Unsplash photo";
            var image = document.createElement("img");
            image.src = photo.urls.thumb;
            image.alt = photo.alt_description || "";
            image.loading = "lazy";
            select.append(image);
            select.addEventListener("click", function () {
                previewPhoto(root, photo, {scroll: true});
            });
            item.append(select);
            addAttribution(item, root, photo);
            results.append(item);
        });
        markSelectedResult(root);
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
        [
            "[data-unsplash-crop-mode]",
            "[data-unsplash-format]",
            "[data-unsplash-quality]"
        ].forEach(function (selector) {
            root.querySelector(selector).addEventListener("input", function () {
                updateTransformControls(root);
            });
        });
        root.querySelector("[data-unsplash-save]").addEventListener("click", function () {
            savePhoto(root);
        });
        root.querySelector("[data-unsplash-cancel]").addEventListener("click", function () {
            window.close();
        });
        initializeFocalPoint(root);
        var selectedPhoto = initialPhoto(root);
        if (selectedPhoto) {
            previewPhoto(root, selectedPhoto);
        }
    }

    document.querySelectorAll("[data-unsplash-popup]").forEach(initialize);
}());
