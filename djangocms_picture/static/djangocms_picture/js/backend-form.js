(function () {
    "use strict";

    function fieldInputs(form, fieldName) {
        return form.querySelectorAll(
            '[name="' + fieldName + '"], [name$="-' + fieldName + '"]'
        );
    }

    function fieldContainers(form, fieldName) {
        var containers = form.querySelectorAll(".field-" + fieldName);
        if (containers.length) {
            return containers;
        }

        var inputs = fieldInputs(form, fieldName);
        var fallback = [];
        inputs.forEach(function (input) {
            var container = input.closest(".form-row, .form-group, .fieldBox, p");
            if (container && fallback.indexOf(container) === -1) {
                fallback.push(container);
            }
        });
        return fallback;
    }

    function setFieldState(form, fieldName, enabled, visible) {
        fieldInputs(form, fieldName).forEach(function (input) {
            input.disabled = !enabled;
        });
        fieldContainers(form, fieldName).forEach(function (container) {
            container.hidden = !visible;
            container.classList.toggle("picture-backend-disabled", !enabled);
        });
    }

    function initializeBackendSelector(selector) {
        var form = selector.closest("form");
        if (!form) {
            return;
        }

        var backends = JSON.parse(selector.dataset.pictureBackends || "{}");

        function update() {
            var selected = backends[selector.value];
            if (!selected) {
                return;
            }

            Object.keys(backends).forEach(function (alias) {
                var fieldName = backends[alias].selectionField;
                setFieldState(form, fieldName, alias === selector.value, alias === selector.value);
            });

            var supported = selected.configurationFields || [];
            var allOptions = [];
            Object.keys(backends).forEach(function (alias) {
                (backends[alias].configurationFields || []).forEach(function (fieldName) {
                    if (allOptions.indexOf(fieldName) === -1) {
                        allOptions.push(fieldName);
                    }
                });
            });
            allOptions.forEach(function (fieldName) {
                setFieldState(form, fieldName, supported.indexOf(fieldName) !== -1, true);
            });
        }

        selector.addEventListener("change", update);
        update();
    }

    function initialize() {
        document.querySelectorAll("[data-picture-backend-selector]").forEach(initializeBackendSelector);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
}());
