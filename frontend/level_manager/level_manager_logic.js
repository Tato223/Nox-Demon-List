const add_level_form = document.querySelector(".add-level-container__form");

add_level_form.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    const endPoint = "http://127.0.0.1:8000/levels";
    const request = {
      level_name: add_level_form.querySelector("#level-name")?.value,
      creator: add_level_form.querySelector("#level-creator")?.value,
      completion_link: add_level_form.querySelector("#completion-link")?.value,
      first_victor: add_level_form.querySelector("#first-victor")?.value,
      list_position: add_level_form.querySelector("#position")?.value,
    };

    const response = await fetch(endPoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    console.log("Request sent to backend:", request);

    if (!response.ok) {
      throw new Error(`HTTP error! Response code: ${response.status}`);
    }

    console.log("Level added successfully!");
  } catch (error) {
    console.error("Fetch failed!", error);
  }
});
