(function () {
    function layoutUserAdminToolbar() {
        if (!document.body.classList.contains("app-user") || !document.body.classList.contains("change-list")) {
            return;
        }

        if (
            !document.body.classList.contains("model-user") &&
            !document.body.classList.contains("model-group")
        ) {
            return;
        }

        document.body.classList.add("pqc-admin-toolbarized");

        var changelist = document.getElementById("changelist");
        var changelistForm = document.getElementById("changelist-form");
        var searchToolbar = document.getElementById("toolbar");
        var objectTools = document.querySelector("#content-main > .object-tools");
        var actions = changelistForm ? changelistForm.querySelector(".actions") : null;

        if (!changelist || !changelistForm || !searchToolbar || !objectTools || !actions) {
            return;
        }

        if (changelist.querySelector(".pqc-admin-user-toolbar-row")) {
            return;
        }

        actions.querySelectorAll("select, input, button, textarea").forEach(function (field) {
            field.setAttribute("form", "changelist-form");
        });

        var objectToolsRow = document.createElement("div");
        objectToolsRow.className = "pqc-admin-user-toolbar-row pqc-admin-user-toolbar-row-object-tools";
        objectToolsRow.appendChild(objectTools);

        var searchRow = document.createElement("div");
        searchRow.className = "pqc-admin-user-toolbar-row pqc-admin-user-toolbar-row-search";
        searchRow.appendChild(searchToolbar);

        var actionsRow = document.createElement("div");
        actionsRow.className = "pqc-admin-user-toolbar-row pqc-admin-user-toolbar-row-actions";
        actionsRow.appendChild(actions);

        changelistForm.parentNode.insertBefore(objectToolsRow, changelistForm);
        changelistForm.parentNode.insertBefore(searchRow, changelistForm);
        changelistForm.parentNode.insertBefore(actionsRow, changelistForm);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", layoutUserAdminToolbar);
    } else {
        layoutUserAdminToolbar();
    }
}());
