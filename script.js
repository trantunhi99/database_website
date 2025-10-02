const tbody = document.getElementById("data-body");
const techTabs = document.getElementById("techTabs");
const filterTissue = document.getElementById("filterTissue");
const filterSpecies = document.getElementById("filterSpecies");
const filterStatus = document.getElementById("filterStatus");
let allData = [];
let currentTech = null;

const sheetCSVUrl =
  "https://docs.google.com/spreadsheets/d/e/2PACX-1vS6BxRrR8H56sDOg9LZA8WGVrQlbVg6vRMxtWgqG1Yo4W3IwgWHS7n6ajB4FNIKyHRwqZXjF9w7hdiN/pub?gid=0&single=true&output=csv";

fetch(sheetCSVUrl)
  .then(res => res.text())
  .then(csvText => {
    const parsed = Papa.parse(csvText, { header: true });
    allData = parsed.data
      .map(row => {
        const normalized = {};
        Object.keys(row).forEach(k => {
          normalized[k.trim().replace(/^\uFEFF/, "")] = row[k];
        });
        return normalized;
      })
      .filter(row => row["dataset_name"] || row["adata_filename"]);

    createTabs(allData);
    populateDropdowns(allData);
    applyFilters(); // initial render
  });

// Create technology tabs
function createTabs(data) {
  const technologies = [...new Set(data.map(d => d["technology"]).filter(Boolean))];

  technologies.forEach((tech, idx) => {
    const btn = document.createElement("button");
    btn.textContent = tech;
    btn.classList.add("tab-btn");
    if (idx === 0) {
      btn.classList.add("active");
      currentTech = tech;
    }
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentTech = tech;
      applyFilters();
    });
    techTabs.appendChild(btn);
  });
}

// Populate dropdowns with checkboxes
function populateDropdowns(data) {
  const tissues = [...new Set(data.map(d => d["general tissue"]).filter(Boolean))];
  const species = [...new Set(data.map(d => d["species"]).filter(Boolean))];
  const statuses = [...new Set(data.map(d => d["cancer or normal or other disease"]).filter(Boolean))];

  function createCheckboxOption(value, container) {
    const wrapper = document.createElement("div");
    wrapper.classList.add("filter-option");

    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = value;

    label.appendChild(input);
    label.append(" " + value);
    wrapper.appendChild(label);
    container.appendChild(wrapper);

    input.addEventListener("change", applyFilters);
  }

  tissues.forEach(t => createCheckboxOption(t, filterTissue));
  species.forEach(sp => createCheckboxOption(sp, filterSpecies));
  statuses.forEach(s => createCheckboxOption(s, filterStatus));
}

// Render rows
function renderTable(data) {
  tbody.innerHTML = "";
  data.forEach(row => {
    const tr = document.createElement("tr");
    [
      "Date",
      "dataset_name",
      "adata_filename",
      "technology",
      "species",
      "general tissue",
      "specific tissue region",
      "cancer or normal or other disease",
      "Spot numbers per sample",
      "Paper",
      "Source",
      "Link to view data"
    ].forEach(col => {
      const td = document.createElement("td");

      if (col === "Source" && row[col]) {
        const a = document.createElement("a");
        a.href = row[col];
        a.textContent = "Paper Link";
        a.target = "_blank";
        td.appendChild(a);
      } else if (col === "Link to view data" && row[col]) {
        const a = document.createElement("a");
        a.href = row[col];
        a.textContent = "View Data";
        a.target = "_blank";
        td.appendChild(a);
      } else {
        td.textContent = row[col] || "";
      }

      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
}

// Apply search + filters + current technology tab
function applyFilters() {
  const search = document.getElementById("searchBox").value.toLowerCase();

  const selectedTissues = Array.from(filterTissue.querySelectorAll("input:checked")).map(i => i.value);
  const selectedSpecies = Array.from(filterSpecies.querySelectorAll("input:checked")).map(i => i.value);
  const selectedStatuses = Array.from(filterStatus.querySelectorAll("input:checked")).map(i => i.value);

  const filtered = allData.filter(row => {
    const matchesTech = !currentTech || row["technology"] === currentTech;

    const text = Object.values(row).join(" ").toLowerCase();
    const matchesSearch = text.includes(search);

    const matchesTissue = selectedTissues.length === 0 || selectedTissues.includes(row["general tissue"]);
    const matchesSpecies = selectedSpecies.length === 0 || selectedSpecies.includes(row["species"]);
    const matchesStatus = selectedStatuses.length === 0 || selectedStatuses.includes(row["cancer or normal or other disease"]);

    return matchesTech && matchesSearch && matchesTissue && matchesSpecies && matchesStatus;
  });

  renderTable(filtered);
}

// Event listeners
document.getElementById("searchBox").addEventListener("keyup", applyFilters);

// Toggle dropdown open/close
document.querySelector(".filter-btn").addEventListener("click", () => {
  document.getElementById("filterDropdown").classList.toggle("active");
});

// Toggle each filter group open/close
document.querySelectorAll(".filter-header").forEach(header => {
  header.addEventListener("click", () => {
    header.parentElement.classList.toggle("active");
  });
});
