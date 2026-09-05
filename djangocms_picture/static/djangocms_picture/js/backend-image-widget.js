(function () {
    "use strict";

    var selectorQuery = "[data-picture-backend-selector]";

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

    function setFieldState(form, fieldName, enabled) {
        fieldInputs(form, fieldName).forEach(function (input) {
            input.disabled = !enabled;
        });
        fieldContainers(form, fieldName).forEach(function (container) {
            container.classList.toggle("picture-backend-disabled", !enabled);
        });
    }

    function setBackendWidgetState(widgetRoot, selectedAlias) {
        if (!widgetRoot) {
            return;
        }
        widgetRoot.querySelectorAll("[data-picture-backend-widget]").forEach(function (container) {
            var alias = container.getAttribute("data-picture-backend-widget");
            var enabled = alias === selectedAlias;
            container.hidden = !enabled;
            container.classList.toggle("picture-backend-disabled", !enabled);
            container.querySelectorAll("input, select, textarea, button").forEach(function (input) {
                input.disabled = !enabled;
            });
        });
    }

    function getBackendConfiguration(selector) {
        try {
            return JSON.parse(selector.getAttribute("data-picture-backends") || "{}");
        } catch (error) {
            return {};
        }
    }

    function updateBackendSelector(selector) {
        var selectedAlias = selector.value;
        var widgetRoot = selector.closest("[data-picture-backend-field]");

        // Picker visibility doesn't depend on the capability metadata. This
        // keeps the reusable widget functional even outside a ModelForm.
        setBackendWidgetState(widgetRoot, selectedAlias);

        var form = selector.closest("form");
        if (!form) {
            return;
        }

        var backends = getBackendConfiguration(selector);
        var selected = backends[selectedAlias];
        if (!selected) {
            return;
        }

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
            setFieldState(form, fieldName, supported.indexOf(fieldName) !== -1);
        });
    }

    function initialize() {
        document.querySelectorAll(selectorQuery).forEach(updateBackendSelector);
    }

    // Delegation also covers plugin forms inserted after DOMContentLoaded.
    document.addEventListener("change", function (event) {
        if (event.target && event.target.matches(selectorQuery)) {
            updateBackendSelector(event.target);
        }
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
}());
