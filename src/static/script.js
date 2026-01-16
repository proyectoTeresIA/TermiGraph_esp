document.addEventListener("DOMContentLoaded", async () => {
    const dropdown = document.getElementById("dropdown");
    const searchInput = document.getElementById("searchInput");
    const selectedDiv = document.getElementById("selected");
    const hiddenInput = document.getElementById("resource_domain");
    const form = document.querySelector("form");

    let options = [];
    let selected = [];

    // ------------------------------
    // Cargar opciones desde Flask
    // ------------------------------
    async function loadOptions() {
        const response = await fetch("/get_options");
        options = await response.json();
        refreshDropdown();
    }

    // ------------------------------
    // Render jerárquico del árbol
    // ------------------------------
    function renderOptions(list, parent, level = 0) {
        list.forEach(item => {
            const div = document.createElement("div");
            div.className = "option";
            div.style.paddingLeft = `${level * 20}px`;
            div.textContent = item.label;
            div.dataset.id = item.id;

            if (selected.find(s => s.id === item.id)) {
                div.classList.add("selected-option");
            }

            div.addEventListener("click", (e) => {
                e.stopPropagation();
                toggleSelect(item);
                refreshDropdown();
            });

            parent.appendChild(div);

            if (item.children && item.children.length > 0) {
                renderOptions(item.children, parent, level + 1);
            }
        });
    }

    function refreshDropdown(filtered = null) {
        dropdown.innerHTML = "";
        renderOptions(filtered || options, dropdown);
    }

    // ------------------------------
    // Selección / Deselección
    // ------------------------------
    function toggleSelect(item) {
        const exists = selected.find(s => s.id === item.id);
        if (exists) {
            selected = selected.filter(s => s.id !== item.id);
        } else {
            selected.push({ id: item.id, label: item.label });
        }
        renderSelected();
        updateHiddenInput();
    }

    // ------------------------------
    // Mostrar seleccionados
    // ------------------------------
    function renderSelected() {
        if (selected.length === 0) {
            selectedDiv.innerHTML = "<i>No hay opciones seleccionadas</i>";
            return;
        }

        selectedDiv.innerHTML = selected.map(s =>
            `<div class="selected-item" data-id="${s.id}">[${s.id}] ${s.label} ❌</div>`
        ).join("");

        document.querySelectorAll(".selected-item").forEach(div => {
            div.addEventListener("click", () => {
                const id = parseInt(div.dataset.id);
                const item = selected.find(s => s.id === id);
                if (item) toggleSelect(item);
                refreshDropdown();
            });
        });
    }

    // ------------------------------
    // Búsqueda recursiva
    // ------------------------------
    searchInput.addEventListener("input", (e) => {
        const term = e.target.value.toLowerCase().trim();
        if (term === "") {
            refreshDropdown();
            return;
        }

        function filterTree(tree) {
            return tree
                .map(node => {
                    if (node.label.toLowerCase().includes(term)) return node;
                    if (node.children) {
                        const filteredChildren = filterTree(node.children);
                        if (filteredChildren.length > 0)
                            return { ...node, children: filteredChildren };
                    }
                    return null;
                })
                .filter(Boolean);
        }

        const filtered = filterTree(options);
        refreshDropdown(filtered);
    });

    // ------------------------------
    // Actualizar input oculto
    // ------------------------------
    function updateHiddenInput() {
        hiddenInput.value = selected.map(s => s.id).join(";");
        hiddenInput.setCustomValidity(""); // limpia error anterior
    }

    // ------------------------------
    // Validación nativa HTML5
    // ------------------------------
    form.addEventListener("submit", (e) => {
        if (hiddenInput.value.trim() === "") {
            hiddenInput.setCustomValidity("Selecciona al menos un dominio EuroVoc.");
            hiddenInput.reportValidity();
            e.preventDefault();
        } else {
            hiddenInput.setCustomValidity("");
        }
    });

    // ------------------------------
    // Iniciar
    // ------------------------------
    await loadOptions();
});
